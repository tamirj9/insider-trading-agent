import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import plotly.express as px
from utils import generate_gpt_summary, detect_cluster_alerts

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
        LIMIT 5000
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

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

# Streamlit setup
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load data
df = load_data()

# Sidebar filters
st.sidebar.header("🧰 Filters")

start_date = st.sidebar.date_input("Start Date", value=df['Date'].min().date())
end_date = st.sidebar.date_input("End Date", value=df['Date'].max().date())

shares_range = st.sidebar.slider("Shares Range", int(df['Shares'].min()), int(df['Shares'].max()), (int(df['Shares'].min()), int(df['Shares'].max())))
amount_range = st.sidebar.slider("Amount Range ($)", int(df['Amount ($)'].min()), int(df['Amount ($)'].max()), (int(df['Amount ($)'].min()), int(df['Amount ($)'].max())))

search_term = st.sidebar.text_input("Search Insider or Company")
group_by = st.sidebar.selectbox("Group By", ["None", "Insider", "Company"])

# Apply filters
filtered_df = df[
    (df['Date'].dt.date >= pd.to_datetime(start_date)) &
    (df['Date'].dt.date <= pd.to_datetime(end_date)) &
    (df['Shares'] >= shares_range[0]) & (df['Shares'] <= shares_range[1]) &
    (df['Amount ($)'] >= amount_range[0]) & (df['Amount ($)'] <= amount_range[1])
]

if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# Grouping
if group_by == "Insider":
    filtered_df = filtered_df.groupby("Insider").agg({
        'Company': 'nunique',
        'Shares': 'sum',
        'Amount ($)': 'sum'
    }).reset_index().rename(columns={'Company': 'Companies'})
elif group_by == "Company":
    filtered_df = filtered_df.groupby("Company").agg({
        'Insider': 'nunique',
        'Shares': 'sum',
        'Amount ($)': 'sum'
    }).reset_index().rename(columns={'Insider': 'Insiders'})

# Charts
if not filtered_df.empty and 'Date' in df.columns:
    st.subheader("📊 Transaction Volume")
    fig = px.bar(
        df,
        x="Date",
        y="Amount ($)",
        color="Company",
        title="Transaction Amount by Date",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

# GPT Summary
if not filtered_df.empty:
    st.subheader("🧠 GPT Summary")
    sample = filtered_df.head(20).to_string(index=False)
    summary = generate_gpt_summary(sample)
    st.info(summary)
else:
    st.warning("No data available for GPT Summary.")

# Cluster Alerts
st.subheader("🚨 Cluster Alerts")
alerts = detect_cluster_alerts(df)
if alerts:
    for alert in alerts:
        st.error(f"{alert['Date']} - {alert['Company']} - ${int(alert['Total Amount']):,} from {len(alert['Insiders'])} insiders")
else:
    st.success("No unusual insider activity detected.")

# Table
st.subheader("📋 Transactions")
st.dataframe(filtered_df, use_container_width=True)

# Quick Stats
st.subheader("📈 Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Total Transactions", len(filtered_df))
if "Insider" in filtered_df.columns:
    col2.metric("Unique Insiders", filtered_df['Insider'].nunique())
if "Company" in filtered_df.columns:
    col3.metric("Unique Companies", filtered_df['Company'].nunique())
