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
        LIMIT 2000
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
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

# ─────────────────────────────────────────────
# Streamlit Layout
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load data
df = load_data()

# Sidebar Filters
st.sidebar.header("🔎 Filter Options")

start_date = st.sidebar.date_input("Start Date", value=df['Date'].min().date())
end_date = st.sidebar.date_input("End Date", value=df['Date'].max().date())

min_shares = st.sidebar.slider("Minimum Shares", 0, int(df['Shares'].max()), 0)
max_shares = st.sidebar.slider("Maximum Shares", 0, int(df['Shares'].max()), int(df['Shares'].max()))

min_amount = st.sidebar.slider("Minimum Amount ($)", 0, int(df['Amount ($)'].max()), 0)
max_amount = st.sidebar.slider("Maximum Amount ($)", 0, int(df['Amount ($)'].max()), int(df['Amount ($)'].max()))

search_term = st.sidebar.text_input("Search Insider or Company")

# Filter Data
filtered_df = df[
    (df['Date'] >= pd.to_datetime(start_date)) &
    (df['Date'] <= pd.to_datetime(end_date)) &
    (df['Shares'] >= min_shares) & (df['Shares'] <= max_shares) &
    (df['Amount ($)'] >= min_amount) & (df['Amount ($)'] <= max_amount)
]

if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# ─────────────────────────────────────────────
# Section 1: Transactions Table
st.subheader("📋 Insider Transactions")
if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)
else:
    st.warning("No transactions match your filters.")

# Section 2: Quick Stats
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", filtered_df['Insider'].nunique())
col2.metric("Unique Companies", filtered_df['Company'].nunique())
col3.metric("Total Transactions", len(filtered_df))

# Section 3: Transaction Volume Chart
st.subheader("📈 Transaction Volume by Day")
chart_df = filtered_df.groupby(filtered_df['Date'].dt.date)['Amount ($)'].sum().reset_index()
chart_df.columns = ['Date', 'Total Amount ($)']
st.line_chart(chart_df.rename(columns={"Date": "index"}).set_index("index"))

# Section 4: GPT Summary of Cluster Alerts
st.subheader("🧠 GPT Summary of Cluster Alerts")
alerts = detect_cluster_alerts(filtered_df)

if alerts:
    for alert in alerts:
        alert_text = f"On {alert['Date']}, multiple insiders ({len(alert['Insiders'])}) at {alert['Company']} traded a total of ${int(alert['Total Amount']):,} across {alert['Count']} transactions."
        with st.expander(f"📌 {alert['Company']} — {alert['Date']} — ${int(alert['Total Amount']):,}"):
            st.markdown(f"**Insiders:** {', '.join(alert['Insiders'])}")
            st.markdown("Generating GPT Summary...")
            summary = generate_gpt_summary(alert_text)
            st.success(summary)
else:
    st.info("No significant cluster alerts in current filters.")
