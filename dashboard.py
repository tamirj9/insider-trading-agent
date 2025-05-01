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
def load_data(limit=1000):
    conn = psycopg2.connect(DATABASE_URL)
    query = f"""
        SELECT 
            t.transaction_id,
            i.name AS insider_name,
            c.company_name AS company_name,
            t.transaction_type,
            t.transaction_date,
            t.reported_date,
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
        'transaction_id': 'ID',
        'insider_name': 'Insider',
        'company_name': 'Company',
        'transaction_type': 'Type',
        'transaction_date': 'Trade Date',
        'reported_date': 'Reported Date',
        'security_title': 'Security',
        'shares': 'Shares',
        'price_per_share': 'Price ($)',
        'total_value': 'Amount ($)'
    }, inplace=True)

    df['ID'] = range(1, len(df) + 1)
    df['Price ($)'] = df['Price ($)'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
    df['Amount ($)'] = df['Amount ($)'].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "")
    df['Trade Date'] = pd.to_datetime(df['Trade Date'])
    df['Reported Date'] = pd.to_datetime(df['Reported Date'])
    return df

# Streamlit app setup
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Record limit selector
row_limit = st.sidebar.selectbox("Number of transactions to display", [100, 500, 1000, 2000], index=2)

# Load data
df = load_data(limit=row_limit)

# Sidebar filters
st.sidebar.header("🔎 Filter Options")
start_date = st.sidebar.date_input("Start Date", value=df['Trade Date'].min().date())
end_date = st.sidebar.date_input("End Date", value=df['Trade Date'].max().date())

insider_filter = st.sidebar.multiselect("Filter by Insider", options=sorted(df['Insider'].unique()))
company_filter = st.sidebar.multiselect("Filter by Company", options=sorted(df['Company'].unique()))

# Apply filters
filtered_df = df[
    (df['Trade Date'].dt.date >= start_date) &
    (df['Trade Date'].dt.date <= end_date)
]
if insider_filter:
    filtered_df = filtered_df[filtered_df['Insider'].isin(insider_filter)]
if company_filter:
    filtered_df = filtered_df[filtered_df['Company'].isin(company_filter)]

# Main table view
st.subheader("📋 Insider Transactions")
if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)
else:
    st.warning("No transactions match your filters.")

# Quick Stats
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", filtered_df['Insider'].nunique())
col2.metric("Unique Companies", filtered_df['Company'].nunique())
col3.metric("Total Transactions", len(filtered_df))
