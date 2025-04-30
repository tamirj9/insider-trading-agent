import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
from utils import detect_cluster_alerts  # GPT summary is temporarily disabled

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

    # Rename for display
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
st.sidebar.header("🧰 Filters")
start_date = st.sidebar.date_input("Start Date", df['Date'].min().date())
end_date = st.sidebar.date_input("End Date", df['Date'].max().date())
shares_min, shares_max = st.sidebar.slider("Shares Range", 0, int(df['Shares'].max()), (100, int(df['Shares'].max())))
amount_min, amount_max = st.sidebar.slider("Amount Range ($)", 0, int(df['Amount ($)'].max()), (0, int(df['Amount ($)'].max())))
search_term = st.sidebar.text_input("Search Insider or Company")
group_option = st.sidebar.selectbox("Group By", ["None", "Company", "Insider"])

# Filter data
filtered_df = df[
    (df['Date'].dt.date >= start_date) &
    (df['Date'].dt.date <= end_date) &
    (df['Shares'].between(shares_min, shares_max)) &
    (df['Amount ($)'].between(amount_min, amount_max))
]

if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# Display filtered data
st.subheader("📋 Transactions")
if group_option == "Company":
    grouped = filtered_df.groupby("Company").agg({
        'Amount ($)': 'sum',
        'Shares': 'sum',
        'Insider': 'nunique'
    }).reset_index().rename(columns={'Insider': 'Unique Insiders'})
    st.dataframe(grouped, use_container_width=True)

elif group_option == "Insider":
    grouped = filtered_df.groupby("Insider").agg({
        'Amount ($)': 'sum',
        'Shares': 'sum',
        'Company': 'nunique'
    }).reset_index().rename(columns={'Company': 'Unique Companies'})
    st.dataframe(grouped, use_container_width=True)

else:
    st.dataframe(filtered_df, use_container_width=True)

# Quick stats
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", filtered_df['Insider'].nunique())
col2.metric("Unique Companies", filtered_df['Company'].nunique())
col3.metric("Total Transactions", len(filtered_df))

# Plot transaction volume
st.subheader("📈 Transaction Volume")
chart = filtered_df.groupby('Date')["Amount ($)"].sum().reset_index()
st.bar_chart(chart.rename(columns={"Date": "index"}).set_index("index"))

# GPT Summary section - temporarily disabled
# st.subheader("🧠 GPT Summary")
# try:
#     cluster_text = filtered_df.to_string(index=False)
#     summary = generate_gpt_summary(cluster_text)
#     st.success(summary)
# except Exception as e:
#     st.warning(f"⚠️ GPT Summary failed: {e}")

# Cluster Alerts
st.subheader("🚨 Cluster Alerts")
try:
    alerts = detect_cluster_alerts(filtered_df)
    if alerts:
        for alert in alerts:
            st.info(f"{alert['Date']}: {alert['Company']} - ${alert['Total Amount']:,.0f} from {alert['Count']} trades")
    else:
        st.write("No significant clusters detected.")
except Exception as e:
    st.error(f"❌ Failed to detect cluster alerts: {e}")
