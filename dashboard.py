import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

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
    
    # Ensure proper timestamp format
    df['Date'] = pd.to_datetime(df['Date'])
    return df

# ───── Streamlit Setup ─────
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# ───── Load and Filter Data ─────
df = load_data()
st.sidebar.header("🔎 Filter Options")

# 📅 Date Range Filter
start_date = st.sidebar.date_input("Start Date", value=df['Date'].min().date())
end_date = st.sidebar.date_input("End Date", value=df['Date'].max().date())

# 🛒 Shares Filter
min_shares = st.sidebar.slider("Minimum Shares", 0, int(df['Shares'].max()), 0)

# 💰 Amount Filter
min_amount = st.sidebar.slider("Minimum Amount ($)", 0, int(df['Amount ($)'].max()), 0)

# 🔍 Search Filter
search_term = st.sidebar.text_input("Search Insider or Company")

# ⛏️ Apply Filters
filtered_df = df[
    (df['Date'].dt.date >= start_date) &
    (df['Date'].dt.date <= end_date) &
    (df['Shares'] >= min_shares) &
    (df['Amount ($)'] >= min_amount)
]

if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# ───── Display Results ─────
st.subheader("📋 Insider Transactions")

if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)
    st.download_button("📥 Download Filtered CSV", filtered_df.to_csv(index=False), "insider_trades.csv", "text/csv")
else:
    st.warning("No transactions match your filters.")

# ───── Quick Stats ─────
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", filtered_df['Insider'].nunique())
col2.metric("Unique Companies", filtered_df['Company'].nunique())
col3.metric("Total Transactions", len(filtered_df))