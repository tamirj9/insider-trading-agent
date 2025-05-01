import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
from plotly.express import bar
import streamlit as st

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

@st.cache_data
def get_top10_companies():
    conn = psycopg2.connect(DATABASE_URL)
    query = """
        SELECT 
            c.company_name AS company,
            SUM(t.total_value) AS total_amount,
            COUNT(*) AS transaction_count,
            MIN(t.transaction_date) AS first_trade,
            MAX(t.transaction_date) AS last_trade
        FROM transactions t
        JOIN issuers c ON t.company_id = c.company_id
        GROUP BY c.company_name
        ORDER BY total_amount DESC
        LIMIT 10
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Render in Streamlit if called directly
if __name__ == '__main__':
    st.set_page_config(layout="wide")
    st.title("🏢 Top 10 Companies by Insider Trade Volume")

    df = get_top10_companies()

    st.subheader("Top 10 Companies (By Total Trade Value)")
    fig = bar(df, x="company", y="total_amount", title="Top 10 by Trade Volume",
              labels={"company": "Company", "total_amount": "Total Trade ($)"},
              hover_data=["transaction_count", "first_trade", "last_trade"])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📄 Full Table of Top 10")
    df["total_amount"] = df["total_amount"].map("${:,.0f}".format)
    st.dataframe(df, use_container_width=True)
