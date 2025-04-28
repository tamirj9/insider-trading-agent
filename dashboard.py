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
            t.transaction_id,
            i.name AS insider,
            c.company_name AS issuer,
            t.transaction_date,
            t.transaction_code,
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
    return df

# Setup
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load data
df = load_data()

# Sidebar Filters
st.sidebar.header("🔎 Filter Options")

# 📅 Timeframe
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime(df['transaction_date'].min()))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime(df['transaction_date'].max()))

# 🔎 Search Insider/Issuer
search_term = st.sidebar.text_input("Search Insider or Company")

# 🛒 Transaction Type
transaction_types = st.sidebar.multiselect(
    "Transaction Type (P: Buy, S: Sell, M: Option Exercise, A: Award)",
    options=df['transaction_code'].unique(),
    default=df['transaction_code'].unique()
)

# 📊 Shares Volume Slider
min_shares = st.sidebar.slider("Minimum Shares", 0, int(df['shares'].max()), 0)

# 💰 Amount Slider
min_amount = st.sidebar.slider("Minimum Transaction Value ($)", 0, int(df['total_value'].max()), 0)

# Apply Filters
filtered_df = df[
    (df['transaction_date'] >= pd.to_datetime(start_date)) &
    (df['transaction_date'] <= pd.to_datetime(end_date)) &
    (df['transaction_code'].isin(transaction_types)) &
    (df['shares'] >= min_shares) &
    (df['total_value'] >= min_amount)
]

if search_term:
    filtered_df = filtered_df[
        filtered_df['insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['issuer'].str.contains(search_term, case=False, na=False)
    ]

# Show Table
st.subheader("📋 Filtered Insider Transactions")
if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)
else:
    st.warning("No transactions match your filters.")

# Quick Stats
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", filtered_df['insider'].nunique())
col2.metric("Unique Issuers", filtered_df['issuer'].nunique())
col3.metric("Total Transactions", len(filtered_df))