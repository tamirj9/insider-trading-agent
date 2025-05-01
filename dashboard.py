import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
from utils import generate_gpt_summary, detect_cluster_alerts
from top10 import display_top10_charts
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Load data from PostgreSQL
@st.cache_data(show_spinner=False)
def load_data(limit=1000):
    conn = psycopg2.connect(DATABASE_URL)
    query = f'''
        SELECT 
            t.transaction_id, 
            i.name AS insider_name, 
            c.company_name AS company_name, 
            t.transaction_type, 
            t.transaction_date, 
            t.filing_date,
            t.created_at AS reported_date,
            t.security_title, 
            t.shares, 
            t.price_per_share, 
            t.total_value
        FROM transactions t
        JOIN insiders i ON t.insider_id = i.insider_id
        JOIN issuers c ON t.company_id = c.company_id
        ORDER BY t.transaction_date DESC
        LIMIT {limit}
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['Trade Date'] = pd.to_datetime(df['transaction_date'])
    df['Filing Date'] = pd.to_datetime(df['filing_date'])
    df['Reported Date'] = pd.to_datetime(df['reported_date'])
    df['Amount ($)'] = df['total_value']
    df['Shares'] = df['shares']
    df['Price ($)'] = df['price_per_share']
    df['Company'] = df['company_name']
    df['Insider'] = df['insider_name']
    df['Type'] = df['transaction_type']
    return df

st.set_page_config(layout="wide")
st.title("📊 PulseReveal - Insider Trading Dashboard")

row_limit = st.sidebar.selectbox("Number of Transactions to Load", [100, 500, 1000, 5000], index=2)
df = load_data(limit=row_limit)

# Sidebar filters
min_reported = df['Reported Date'].min()
default_start = min_reported.date() if pd.notnull(min_reported) else datetime.date.today() - datetime.timedelta(days=7)
start_date = st.sidebar.date_input("Start Date", value=default_start)
end_date = st.sidebar.date_input("End Date", value=datetime.date.today())

company_filter = st.sidebar.text_input("Search Company")
insider_filter = st.sidebar.text_input("Search Insider")

df_filtered = df[(df['Reported Date'].dt.date >= start_date) & (df['Reported Date'].dt.date <= end_date)]

if company_filter:
    df_filtered = df_filtered[df_filtered['Company'].str.contains(company_filter, case=False)]
if insider_filter:
    df_filtered = df_filtered[df_filtered['Insider'].str.contains(insider_filter, case=False)]

# Transaction Volume by Day
st.subheader("📈 Transaction Volume by Day")
daily_volume = df_filtered.groupby(df_filtered['Reported Date'].dt.date)['Amount ($)'].sum().reset_index()
fig = px.line(daily_volume, x='Reported Date', y='Amount ($)', title='Transaction Volume by Day')
st.plotly_chart(fig, use_container_width=True)

# GPT Summary of Cluster Alerts
st.subheader("🧠 GPT Summary of Cluster Alerts")
cluster_alerts = detect_cluster_alerts(df_filtered)
if not cluster_alerts:
    st.info("No cluster alerts detected in selected date range.")
else:
    for alert in cluster_alerts:
        with st.expander(f"📌 {alert['Company']} — {alert['Date']} — ${alert['Total Amount']:,}"):
            insiders = ", ".join(alert['Insiders'])
            st.markdown(f"**Insiders:** {insiders}")
            st.write("Generating GPT Summary...")
            summary = generate_gpt_summary(f"Company: {alert['Company']}\nDate: {alert['Date']}\nAmount: ${alert['Total Amount']:,}\nInsiders: {insiders}")
            st.success(summary)

# Top 10 Charts
display_top10_charts(df_filtered)

# Transactions Table
st.subheader("📋 Transactions")
display_columns = ['Insider', 'Company', 'Type', 'Trade Date', 'Filing Date', 'Reported Date', 'Shares', 'Price ($)', 'Amount ($)', 'security_title']
df_display = df_filtered[display_columns].copy()
df_display.index += 1
st.dataframe(df_display, use_container_width=True)
