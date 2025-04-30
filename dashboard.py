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

# Streamlit app setup
st.set_page_config(page_title="PulseReveal Dashboard", page_icon="📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Load data
df = load_data()

# Sidebar filters
st.sidebar.header("🧰 Filters")

# 📅 Timeframe selector
start_date = st.sidebar.date_input("Start Date", value=df['Date'].min().date())
end_date = st.sidebar.date_input("End Date", value=df['Date'].max().date())

# 🛒 Shares slider
min_shares, max_shares = st.sidebar.slider("Shares Range", 0, int(df['Shares'].max()), (100, int(df['Shares'].max())))

# 💰 Amount slider
min_amount, max_amount = st.sidebar.slider("Amount Range ($)", 0, int(df['Amount ($)'].max()), (0, int(df['Amount ($)'].max())))

# 🔎 Search
search_term = st.sidebar.text_input("Search Insider or Company")

# 🔀 Group By
group_by = st.sidebar.selectbox("Group By", ["None", "Insider", "Company"])

# Apply filters
filtered_df = df[
    (df['Date'] >= pd.to_datetime(start_date)) &
    (df['Date'] <= pd.to_datetime(end_date)) &
    (df['Shares'] >= min_shares) &
    (df['Shares'] <= max_shares) &
    (df['Amount ($)'] >= min_amount) &
    (df['Amount ($)'] <= max_amount)
]

if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# 🧮 Grouping (optional)
if group_by == "Insider":
    filtered_df = filtered_df.groupby("Insider", as_index=False).agg({
        "Company": "nunique",
        "Shares": "sum",
        "Amount ($)": "sum"
    })
elif group_by == "Company":
    filtered_df = filtered_df.groupby("Company", as_index=False).agg({
        "Insider": "nunique",
        "Shares": "sum",
        "Amount ($)": "sum"
    })

# 📊 Chart
st.subheader("📊 Transaction Volume")
if not filtered_df.empty and "Date" in filtered_df.columns:
    chart = px.bar(filtered_df, x="Date", y="Amount ($)", color="Company", title="Transaction Volume by Company")
    st.plotly_chart(chart, use_container_width=True)

# 🧠 GPT Summary
st.subheader("🧠 GPT Summary")
gpt_summary_text = "\n".join(
    f"{row['Date'].strftime('%Y-%m-%d')} - {row['Insider']} bought ${row['Amount ($)']:.0f} of {row['Company']}"
    for _, row in filtered_df.head(20).iterrows()
)
summary_result = generate_gpt_summary(gpt_summary_text)
st.info(summary_result)

# 🚨 Cluster Alerts
st.subheader("🚨 Cluster Alerts")
alerts = detect_cluster_alerts(df)
if alerts:
    for alert in alerts:
        st.warning(f"{alert['Date']}: {alert['Company']} - ${alert['Total Amount']:.0f} from {alert['Count']} trades")
else:
    st.success("No cluster alerts at this time.")

# 📋 Table
st.subheader("📋 Transactions")
st.dataframe(filtered_df, use_container_width=True)

# 📈 Quick Stats
st.subheader("📈 Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", df['Insider'].nunique())
col2.metric("Unique Companies", df['Company'].nunique())
col3.metric("Total Records", len(df))
