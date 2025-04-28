import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", 8000))  # <- Add this line!

# Connect to your PostgreSQL database
@st.cache_data
def load_data():
    conn = psycopg2.connect(DATABASE_URL)
    query = """
        SELECT 
            insider,
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

# Streamlit app layout
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load data
df = load_data()

# Show the latest 100 insider trades
st.subheader("Latest Insider Transactions")
st.dataframe(df, use_container_width=True)

# Quick stats
st.subheader("Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", df['insider'].nunique())
col2.metric("Unique Issuers", df['issuer'].nunique())
col3.metric("Total Transactions", len(df))

# IMPORTANT: Add this to run on Railway PORT!
if __name__ == "__main__":
    st.run(port=PORT)