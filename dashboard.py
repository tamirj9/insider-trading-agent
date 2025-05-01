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
@st.cache_data(show_spinner="Loading data...")
def load_data(limit=1000):
    conn = psycopg2.connect(DATABASE_URL)
    query = f"""
        SELECT 
            t.transaction_id,
            i.name AS insider_name,
            c.company_name AS company_name,
            t.transaction_type,
            t.transaction_code,
            t.transaction_date,
            t.reported_date,
            t.filing_date,
            t.security_title,
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
        'transaction_type': 'Type',
        'transaction_date': 'Trade Date',
        'reported_date': 'Reported Date',
        'filing_date': 'Filing Date',
        'security_title': 'Security',
        'shares': 'Shares',
        'price_per_share': 'Price ($)',
        'total_value': 'Amount ($)'
    }, inplace=True)

    df['Trade Date'] = pd.to_datetime(df['Trade Date'])
    df['Reported Date'] = pd.to_datetime(df['Reported Date'])
    df['Filing Date'] = pd.to_datetime(df['Filing Date'])

    return df

# Streamlit App Config
st.set_page_config("PulseReveal Dashboard", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Filters and controls
row_limit = st.sidebar.selectbox("Show rows", [100, 500, 1000], index=2)
df = load_data(limit=row_limit)

st.sidebar.header("🔎 Filter Options")
start_date = st.sidebar.date_input("Start Date", value=df['Reported Date'].min().date())
end_date = st.sidebar.date_input("End Date", value=df['Reported Date'].max().date())
search_term = st.sidebar.text_input("Search Insider or Company")

# Apply filters
filtered_df = df[
    (df['Reported Date'].dt.date >= start_date) &
    (df['Reported Date'].dt.date <= end_date)
]

if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# Format columns
filtered_df['Price ($)'] = filtered_df['Price ($)'].apply(lambda x: f"${x:,.2f}")
filtered_df['Amount ($)'] = filtered_df['Amount ($)'].apply(lambda x: f"${x:,.0f}")

# Reset index to start from 1
filtered_df.index = range(1, len(filtered_df) + 1)

# Quick Stats
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", filtered_df['Insider'].nunique())
col2.metric("Unique Companies", filtered_df['Company'].nunique())
col3.metric("Total Transactions", len(filtered_df))

# Transaction Table
st.subheader("📋 Insider Transactions")
st.dataframe(filtered_df, use_container_width=True)

# Transaction Volume Chart
st.subheader("📉 Transaction Volume by Day")
daily_volume = filtered_df.groupby('Reported Date')['Amount ($)'].apply(lambda x: x.str.replace("$", "").str.replace(",", "").astype(float)).sum().reset_index()
st.line_chart(data=daily_volume, x='Reported Date', y='Amount ($)')

# GPT Cluster Summaries
st.subheader("🧠 GPT Summary of Cluster Alerts")
clusters = detect_cluster_alerts(filtered_df)

for alert in clusters:
    with st.expander(f"📌 {alert['Company']} — {alert['Date']} — ${alert['Total Amount']:,.0f}"):
        st.markdown(f"**Insiders:** {', '.join(alert['Insiders'])}")
        st.markdown("Generating GPT Summary...")
        summary = generate_gpt_summary(
            f"On {alert['Date']}, {len(alert['Insiders'])} insiders at {alert['Company']} traded ${alert['Total Amount']:,.0f} in {alert['Count']} transactions."
        )
        st.success(summary)
