import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
from utils import generate_gpt_summary, detect_cluster_alerts

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connect to PostgreSQL
@st.cache_data
def load_data(limit=1000):
    conn = psycopg2.connect(DATABASE_URL)
    query = f"""
        SELECT 
            t.transaction_id,
            i.name AS insider_name,
            c.company_name AS company_name,
            t.transaction_type,
            t.transaction_date,
            t.filing_date,
            t.created_at AS reported_date,
            t.security_title,
            t.transaction_code,
            t.shares,
            t.price_per_share,
            t.total_value
        FROM transactions t
        JOIN insiders i ON t.insider_id = i.insider_id
        JOIN issuers c ON t.company_id = c.company_id
        ORDER BY t.transaction_date DESC
        LIMIT {limit}
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df.rename(columns={
        'insider_name': 'Insider',
        'company_name': 'Company',
        'transaction_date': 'Trade Date',
        'filing_date': 'Filing Date',
        'reported_date': 'Reported Date',
        'transaction_type': 'Type',
        'transaction_code': 'Code',
        'security_title': 'Security',
        'shares': 'Shares',
        'price_per_share': 'Price ($)',
        'total_value': 'Amount ($)'
    }, inplace=True)

    df['Trade Date'] = pd.to_datetime(df['Trade Date'], errors='coerce')
    df['Reported Date'] = pd.to_datetime(df['Reported Date'], errors='coerce')
    return df

# Streamlit app setup
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load data
row_limit = st.sidebar.selectbox("Show Transactions", [100, 500, 1000], index=2)
df = load_data(limit=row_limit)

# Sidebar filters
st.sidebar.header("🔎 Filter Options")

# 📅 Timeframe filter with fallback for NaT
min_date = df['Reported Date'].min()
max_date = df['Reported Date'].max()
if pd.isna(min_date) or pd.isna(max_date):
    min_date = pd.to_datetime("2020-01-01")
    max_date = pd.Timestamp.today()

start_date = st.sidebar.date_input("Start Date", value=min_date.date())
end_date = st.sidebar.date_input("End Date", value=max_date.date())

# Shares filter
min_shares, max_shares = int(df['Shares'].min()), int(df['Shares'].max())
shares_range = st.sidebar.slider("Shares Range", min_shares, max_shares, (min_shares, max_shares))

# Amount filter
min_amount, max_amount = int(df['Amount ($)'].min()), int(df['Amount ($)'].max())
amount_range = st.sidebar.slider("Amount Range ($)", min_amount, max_amount, (min_amount, max_amount))

# Search
search_term = st.sidebar.text_input("Search Insider or Company")

# Grouping
group_by = st.sidebar.selectbox("Group By", ["None", "Insider", "Company"])

# Apply filters
filtered_df = df[
    (df['Reported Date'].dt.date >= start_date) &
    (df['Reported Date'].dt.date <= end_date) &
    (df['Shares'] >= shares_range[0]) & (df['Shares'] <= shares_range[1]) &
    (df['Amount ($)'] >= amount_range[0]) & (df['Amount ($)'] <= amount_range[1])
]
if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# Display
if group_by == "Insider":
    grouped = filtered_df.groupby("Insider").agg({
        "Amount ($)": "sum",
        "Shares": "sum",
        "Company": pd.Series.nunique
    }).reset_index()
    st.subheader("📋 Grouped by Insider")
    st.dataframe(grouped, use_container_width=True)

elif group_by == "Company":
    grouped = filtered_df.groupby("Company").agg({
        "Amount ($)": "sum",
        "Shares": "sum",
        "Insider": pd.Series.nunique
    }).reset_index()
    st.subheader("📋 Grouped by Company")
    st.dataframe(grouped, use_container_width=True)

else:
    st.subheader("📋 Insider Transactions")
    df_display = filtered_df.copy()
    df_display.index += 1  # Start from 1
    df_display['Amount ($)'] = df_display['Amount ($)'].map('${:,.0f}'.format)
    df_display['Price ($)'] = df_display['Price ($)'].map('${:,.2f}'.format)
    st.dataframe(df_display, use_container_width=True)

# 📊 Quick Stats
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", filtered_df['Insider'].nunique())
col2.metric("Unique Companies", filtered_df['Company'].nunique())
col3.metric("Total Transactions", len(filtered_df))

# 📈 Charts
import plotly.express as px
st.subheader("📉 Transaction Volume by Day")
daily = filtered_df.groupby(filtered_df['Reported Date'].dt.date)['Amount ($)'].sum().reset_index()
fig = px.line(daily, x='Reported Date', y='Amount ($)', title="Transaction Volume by Day")
st.plotly_chart(fig, use_container_width=True)

# 🧠 GPT Summary for cluster alerts
st.subheader("🧠 GPT Summary of Cluster Alerts")
cluster_alerts = detect_cluster_alerts(filtered_df)

for alert in cluster_alerts:
    with st.expander(f"📌 {alert['Company']} — {alert['Date']} — ${alert['Total Amount']:,.0f}"):
        st.markdown(f"**Insiders:** {', '.join(alert['Insiders'])}")
        st.write("Generating GPT Summary...")
        summary = generate_gpt_summary(
            f"Date: {alert['Date']}, Company: {alert['Company']}, Total Amount: ${alert['Total Amount']:,.0f}, " +
            f"Insiders: {', '.join(alert['Insiders'])}"
        )
        st.success(summary)
