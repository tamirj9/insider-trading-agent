import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connect to your PostgreSQL database
@st.cache_data
def load_data():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        query = """
            SELECT 
                transaction_id,
                insider_id,
                company_id,
                transaction_date,
                transaction_code,
                security_title,
                transaction_type,
                shares,
                price_per_share,
                total_value,
                form_type,
                filing_date,
                created_at
            FROM transactions
            ORDER BY filing_date DESC
            LIMIT 100
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database connection or query failed: {e}")
        return pd.DataFrame()

# Streamlit app layout
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load data
df = load_data()

# Show the latest 100 insider trades
if df.empty:
    st.warning("No data available or failed to fetch data.")
else:
    st.subheader("Latest Insider Transactions")
    st.dataframe(df, use_container_width=True)

    # (Optional) Add quick stats
    st.subheader("Quick Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Unique Insiders", df['insider_id'].nunique())
    col2.metric("Unique Companies", df['company_id'].nunique())
    col3.metric("Total Transactions", len(df))