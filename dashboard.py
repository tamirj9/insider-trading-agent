import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

# ─── Load environment variables ───
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# ─── Database Connection ───
@st.cache_data(ttl=600)  # cache the data for 10 minutes
def load_data():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        query = """
            SELECT 
                insider_id AS insider,    -- Fix applied here
                issuer,
                transactiondate,
                transactioncode,
                securitytitle,
                shares,
                price
            FROM transactions
            ORDER BY transactiondate DESC
            LIMIT 100
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database connection or query failed: {e}")
        return pd.DataFrame()

# ─── Streamlit App Layout ───
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# ─── Load and Display Data ───
df = load_data()

if df.empty:
    st.warning("No data available or failed to fetch data.")
else:
    st.subheader("Latest Insider Transactions")
    st.dataframe(df, use_container_width=True)

    # ─── Quick Stats ───
    st.subheader("Quick Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Unique Insiders", df['insider'].nunique())
    col2.metric("Unique Issuers", df['issuer'].nunique())
    col3.metric("Total Transactions", len(df))