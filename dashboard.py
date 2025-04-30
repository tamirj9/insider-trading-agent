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
@st.cache_data(ttl=3600)
def load_data():
    conn = psycopg2.connect(DATABASE_URL)
    query = """
        SELECT 
            i.name AS insider_name,
            c.company_name AS issuer_name,
            t.transaction_date,
            t.security_title,
            t.shares,
            t.price_per_share,
            t.total_value
        FROM transactions t
        JOIN insiders i ON t.insider_id = i.insider_id
        JOIN issuers c ON t.company_id = c.company_id
        ORDER BY t.transaction_date DESC
        LIMIT 1000
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Rename for user-friendly display
    df.rename(columns={
        'insider_name': 'Insider',
        'issuer_name': 'Company',
        'transaction_date': 'Date',
        'security_title': 'Security',
        'shares': 'Shares',
        'price_per_share': 'Price ($)',
        'total_value': 'Amount ($)'
    }, inplace=True)

    # Convert Date to Timestamp correctly
    df['Date'] = pd.to_datetime(df['Date'])
    return df

# Streamlit app setup
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load data
df = load_data()

# Sidebar filters
st.sidebar.header("🧰 Filters")
start_date = st.sidebar.date_input("Start Date", value=df['Date'].min().date())
end_date = st.sidebar.date_input("End Date", value=df['Date'].max().date())

shares_range = st.sidebar.slider("Shares Range", 0, int(df['Shares'].max()), (100, int(df['Shares'].max())))
amount_range = st.sidebar.slider("Amount Range ($)", 0, int(df['Amount ($)'].max()), (0, int(df['Amount ($)'].max())))
search_term = st.sidebar.text_input("Search Insider or Company")
group_by = st.sidebar.selectbox("Group By", ["None", "Insider", "Company"])

# Filter data
filtered_df = df[
    (df['Date'] >= pd.to_datetime(start_date)) &
    (df['Date'] <= pd.to_datetime(end_date)) &
    (df['Shares'] >= shares_range[0]) & (df['Shares'] <= shares_range[1]) &
    (df['Amount ($)'] >= amount_range[0]) & (df['Amount ($)'] <= amount_range[1])
].copy()

if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# Main Display Order: 1. Table
st.subheader("📋 Transactions")
if not filtered_df.empty:
    if group_by == "Insider":
        grouped = filtered_df.groupby("Insider").agg({
            "Company": "nunique",
            "Amount ($)": "sum",
            "Shares": "sum"
        }).rename(columns={"Company": "Companies", "Amount ($)": "Total Amount", "Shares": "Total Shares"})
        st.dataframe(grouped.reset_index(), use_container_width=True)
    elif group_by == "Company":
        grouped = filtered_df.groupby("Company").agg({
            "Insider": "nunique",
            "Amount ($)": "sum",
            "Shares": "sum"
        }).rename(columns={"Insider": "Insiders", "Amount ($)": "Total Amount", "Shares": "Total Shares"})
        st.dataframe(grouped.reset_index(), use_container_width=True)
    else:
        st.dataframe(filtered_df, use_container_width=True)
else:
    st.warning("No transactions match your filters.")

# 2. Quick Stats
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", filtered_df['Insider'].nunique())
col2.metric("Unique Companies", filtered_df['Company'].nunique())
col3.metric("Total Transactions", len(filtered_df))

# 3. Transaction Volume Chart
import plotly.express as px

if not filtered_df.empty:
    chart_df = filtered_df.groupby("Date")["Amount ($)"].sum().reset_index()
    fig = px.bar(chart_df, x="Date", y="Amount ($)", title="Transaction Volume", height=400)
    st.plotly_chart(fig, use_container_width=True)

# 4. GPT Summary
st.subheader("🧠 GPT Summary")
if not filtered_df.empty:
    try:
        gpt_summary = generate_gpt_summary(filtered_df.head(10).to_string(index=False))
        st.success(gpt_summary)
    except Exception as e:
        st.warning(f"⚠️ GPT Summary failed: {e}")

# 5. Cluster Alerts
st.subheader("🚨 Cluster Alerts")
alerts = detect_cluster_alerts(filtered_df)
if alerts:
    for alert in alerts:
        st.info(f"{alert['Date']}: {alert['Company']} - ${int(alert['Total Amount']):,} from {alert['Count']} trades")
else:
    st.write("No cluster alerts found.")
