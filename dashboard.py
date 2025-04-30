import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
from utils import generate_gpt_summary, detect_cluster_alerts

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
        LIMIT 5000
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

    df['Date'] = pd.to_datetime(df['Date'])
    return df

# Streamlit page setup
st.set_page_config(page_title="PulseReveal Dashboard", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load data
df = load_data()

# Sidebar filters
st.sidebar.header("🧰 Filters")

# Time range
start_date = st.sidebar.date_input("Start Date", value=df['Date'].min().date())
end_date = st.sidebar.date_input("End Date", value=df['Date'].max().date())

# Range sliders
min_shares, max_shares = st.sidebar.slider("Shares Range", 
    min_value=int(df['Shares'].min()), 
    max_value=int(df['Shares'].max()),
    value=(int(df['Shares'].min()), int(df['Shares'].max()))
)

min_amt, max_amt = st.sidebar.slider("Amount Range ($)", 
    min_value=int(df['Amount ($)'].min()), 
    max_value=int(df['Amount ($)'].max()),
    value=(int(df['Amount ($)'].min()), int(df['Amount ($)'].max()))
)

search = st.sidebar.text_input("Search Insider or Company")
group_by = st.sidebar.selectbox("Group By", ["None", "Insider", "Company"])

# Filtered data
filtered_df = df[
    (df['Date'] >= pd.to_datetime(start_date)) &
    (df['Date'] <= pd.to_datetime(end_date)) &
    (df['Shares'] >= min_shares) &
    (df['Shares'] <= max_shares) &
    (df['Amount ($)'] >= min_amt) &
    (df['Amount ($)'] <= max_amt)
]

if search:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search, case=False, na=False) |
        filtered_df['Company'].str.contains(search, case=False, na=False)
    ]

# Grouping
if group_by == "Insider":
    filtered_df = filtered_df.groupby("Insider", as_index=False).agg({
        "Company": "nunique",
        "Shares": "sum",
        "Amount ($)": "sum"
    }).rename(columns={"Company": "#Companies"})
elif group_by == "Company":
    filtered_df = filtered_df.groupby("Company", as_index=False).agg({
        "Insider": "nunique",
        "Shares": "sum",
        "Amount ($)": "sum"
    }).rename(columns={"Insider": "#Insiders"})

# Main table
st.subheader("📋 Transactions")
st.dataframe(filtered_df, use_container_width=True)

# Quick stats
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", df['Insider'].nunique())
col2.metric("Unique Companies", df['Company'].nunique())
col3.metric("Total Trades", len(df))

# Bar charts
import plotly.express as px

st.subheader("📈 Transaction Volume")
vol_chart = px.bar(
    df.groupby(df['Date'].dt.date)['Amount ($)'].sum().reset_index(),
    x='Date', y='Amount ($)',
    title="Daily Transaction Amount",
)
st.plotly_chart(vol_chart, use_container_width=True)

company_chart = px.bar(
    df.groupby("Company")['Amount ($)'].sum().nlargest(10).reset_index(),
    x='Company', y='Amount ($)', orientation='v',
    title="Top 10 Companies by Amount ($)"
)
st.plotly_chart(company_chart, use_container_width=True)

# GPT Summary
st.subheader("🧠 GPT Summary")
try:
    summary_text = generate_gpt_summary(filtered_df.head(100).to_string(index=False))
    st.info(summary_text)
except Exception as e:
    st.warning(f"⚠️ GPT Summary failed: {e}")

# Cluster Alerts
st.subheader("🚨 Cluster Alerts")
alerts = detect_cluster_alerts(df)
if alerts:
    for a in alerts:
        st.markdown(f"<div style='background-color:#e8f1ff;padding:10px;border-radius:8px;'>
            <strong>{a['Date']}:</strong> {a['Company']} - ${a['Total Amount']:,.0f} from {a['Count']} trades
        </div>", unsafe_allow_html=True)
else:
    st.info("No cluster alerts detected.")