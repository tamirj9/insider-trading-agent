import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
from utils import generate_gpt_summary, detect_cluster_alerts
from alerts import send_cluster_alert
import plotly.express as px

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connect to PostgreSQL
@st.cache_data

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
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Rename for UI
    df.rename(columns={
        'insider_name': 'Insider',
        'issuer_name': 'Company',
        'transaction_date': 'Date',
        'security_title': 'Security',
        'shares': 'Shares',
        'price_per_share': 'Price ($)',
        'total_value': 'Amount ($)'
    }, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'])
    return df

# Setup page
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load
df = load_data()

# Sidebar Filters
st.sidebar.header("🧰 Filters")
start_date = st.sidebar.date_input("Start Date", df['Date'].min().date())
end_date = st.sidebar.date_input("End Date", df['Date'].max().date())
shares_range = st.sidebar.slider("Shares Range", 0, int(df['Shares'].max()), (100, int(df['Shares'].max())))
amount_range = st.sidebar.slider("Amount Range ($)", 0, int(df['Amount ($)'].max()), (0, int(df['Amount ($)'].max())))
search_term = st.sidebar.text_input("Search Insider or Company")
group_option = st.sidebar.selectbox("Group By", ["None", "Insider", "Company"])

# Filters
filtered_df = df[
    (df['Date'] >= pd.to_datetime(start_date)) &
    (df['Date'] <= pd.to_datetime(end_date)) &
    (df['Shares'].between(shares_range[0], shares_range[1])) &
    (df['Amount ($)'].between(amount_range[0], amount_range[1]))
]

if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# 1. Transactions Table
st.subheader("📋 Transactions")
if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)
    csv = filtered_df.to_csv(index=False)
    st.download_button("💾 Download CSV", csv, "insider_trades.csv", "text/csv")
else:
    st.warning("No data matches your filters.")

# 2. Stats
st.subheader("📊 Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", filtered_df['Insider'].nunique())
col2.metric("Unique Companies", filtered_df['Company'].nunique())
col3.metric("Total Transactions", len(filtered_df))

# 3. Charts
st.subheader("📈 Transaction Volume")
if not filtered_df.empty:
    chart_data = filtered_df.groupby(['Date', 'Company'])['Amount ($)'].sum().reset_index()
    fig = px.bar(chart_data, x='Date', y='Amount ($)', color='Company', title="Transaction Volume by Company")
    st.plotly_chart(fig, use_container_width=True)

# 4. GPT Summary
st.subheader("🧠 GPT Summary")
try:
    gpt_text = filtered_df.head(10).to_markdown(index=False)
    summary = generate_gpt_summary(gpt_text)
    st.success(summary)
except Exception as e:
    st.info(f"⚠️ GPT Summary failed: {e}")

# 5. Cluster Alerts
st.subheader("🚨 Cluster Alerts")
alerts = detect_cluster_alerts(filtered_df)
if alerts:
    for alert in alerts:
        st.markdown(f"**{alert['Date']}**: {alert['Company']} - ${alert['Total Amount']:,.0f} from {alert['Count']} trades")
        send_cluster_alert(f"🚨 {alert['Company']} on {alert['Date']} - ${alert['Total Amount']:,.0f} from {alert['Count']} trades")
else:
    st.info("No cluster alerts detected.")
