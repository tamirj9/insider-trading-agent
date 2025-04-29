import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connect to PostgreSQL and load data
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
    
    # Rename columns for display
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

# Streamlit layout
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load data
df = load_data()

# Sidebar filters
st.sidebar.header("🔎 Filter Options")

# 📅 Timeframe
start_date = pd.to_datetime(st.sidebar.date_input("Start Date", value=df['Date'].min().date()))
end_date = pd.to_datetime(st.sidebar.date_input("End Date", value=df['Date'].max().date()))

# 🛒 Shares Range
min_shares, max_shares = st.sidebar.slider(
    "Shares Range",
    int(df['Shares'].min()),
    int(df['Shares'].max()),
    (int(df['Shares'].min()), int(df['Shares'].max()))
)

# 💰 Amount Range
min_amount, max_amount = st.sidebar.slider(
    "Amount Range ($)",
    int(df['Amount ($)'].min()),
    int(df['Amount ($)'].max()),
    (int(df['Amount ($)'].min()), int(df['Amount ($)'].max()))
)

# 🔍 Search
search_term = st.sidebar.text_input("Search Insider or Company")

# Apply filters
filtered_df = df[
    (df['Date'] >= start_date) &
    (df['Date'] <= end_date) &
    (df['Shares'] >= min_shares) &
    (df['Shares'] <= max_shares) &
    (df['Amount ($)'] >= min_amount) &
    (df['Amount ($)'] <= max_amount)
]

if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# Display results
st.subheader("📋 Insider Transactions")

if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)
    st.download_button("📥 Download CSV", filtered_df.to_csv(index=False), "insider_trades.csv", "text/csv")
else:
    st.warning("No transactions match your filters.")

# Quick Stats
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", filtered_df['Insider'].nunique())
col2.metric("Unique Companies", filtered_df['Company'].nunique())
col3.metric("Total Transactions", len(filtered_df))