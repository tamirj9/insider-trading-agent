import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
from dotenv import load_dotenv
import os
from utils import generate_gpt_summary, detect_cluster_alerts
from top10 import display_top10_charts

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def load_data(limit=1000):
    conn = psycopg2.connect(DATABASE_URL)
    query = f'''
        SELECT t.transaction_id, i.name AS insider_name, c.company_name AS company_name,
               t.transaction_code AS transaction_type,
               t.transaction_date, t.filing_date, t.reported_date,
               t.security_title, t.transaction_type AS type,
               t.shares, t.price_per_share, t.total_value
        FROM transactions t
        JOIN insiders i ON t.insider_id = i.insider_id
        JOIN issuers c ON t.company_id = c.company_id
        ORDER BY t.transaction_date DESC
        LIMIT {limit}
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.set_page_config(layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.caption("Stay updated on the latest insider trades.")

# Load data
row_limit = st.sidebar.selectbox("Number of transactions to show", [100, 500, 1000], index=2)
df = load_data(limit=row_limit)

# Convert dates
for col in ["transaction_date", "filing_date", "reported_date"]:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# Rename columns
column_renames = {
    "insider_name": "Insider",
    "company_name": "Company",
    "transaction_type": "Type",
    "transaction_date": "Trade Date",
    "filing_date": "Filing Date",
    "reported_date": "Reported Date",
    "security_title": "Security",
    "shares": "Shares",
    "price_per_share": "Price ($)",
    "total_value": "Amount ($)"
}
df.rename(columns=column_renames, inplace=True)

# Sidebar filters
start_date = st.sidebar.date_input("Start Date", value=df['Reported Date'].min().date())
end_date = st.sidebar.date_input("End Date", value=df['Reported Date'].max().date())

min_shares = int(df["Shares"].min())
max_shares = int(df["Shares"].max())
shares_range = st.sidebar.slider("Shares Range", min_value=min_shares, max_value=max_shares,
                                  value=(min_shares, max_shares))

min_amount = int(df["Amount ($)"].min())
max_amount = int(df["Amount ($)"].max())
amount_range = st.sidebar.slider("Amount Range ($)", min_value=min_amount, max_value=max_amount,
                                  value=(min_amount, max_amount))

search_term = st.sidebar.text_input("Search Insider or Company")
group_by = st.sidebar.selectbox("Group By", ["None", "Insider", "Company"])

# Filtered data
filtered_df = df[(df['Reported Date'].dt.date >= pd.to_datetime(start_date).date()) &
                 (df['Reported Date'].dt.date <= pd.to_datetime(end_date).date()) &
                 (df['Shares'].between(*shares_range)) &
                 (df['Amount ($)'].between(*amount_range))]

if search_term:
    filtered_df = filtered_df[
        filtered_df['Insider'].str.contains(search_term, case=False, na=False) |
        filtered_df['Company'].str.contains(search_term, case=False, na=False)
    ]

# Show charts
st.subheader("📊 Transaction Volume by Day")
daily_volume = filtered_df.groupby(filtered_df['Reported Date'].dt.date)["Amount ($)"].sum().reset_index()
fig = px.line(daily_volume, x='Reported Date', y='Amount ($)', title="Transaction Volume by Day")
st.plotly_chart(fig, use_container_width=True)

# Top 10 Companies & Insiders
display_top10_charts(filtered_df)

# GPT Summaries by cluster
st.subheader("🧠 GPT Summary of Cluster Alerts")
cluster_alerts = detect_cluster_alerts(filtered_df)

if cluster_alerts:
    for alert in cluster_alerts:
        with st.expander(f"📌 {alert['Company']} — {alert['Date']} — ${alert['Total Amount']:,}"):
            insiders = ", ".join(alert['Insiders'])
            st.markdown(f"**Insiders:** {insiders}")
            st.markdown("Generating GPT Summary...")
            summary = generate_gpt_summary(
                f"On {alert['Date']}, the following insiders traded in {alert['Company']} totaling ${alert['Total Amount']:,}: {insiders}"
            )
            st.success(summary)
else:
    st.info("No cluster alerts detected in the selected date range.")

# Transactions Table
st.subheader("📋 Transactions")
filtered_df.reset_index(drop=True, inplace=True)
filtered_df.index += 1

format_dollar = lambda x: f"${x:,.0f}" if pd.notnull(x) else ""
filtered_df["Amount ($)"] = filtered_df["Amount ($)"].apply(format_dollar)
filtered_df["Price ($)"] = filtered_df["Price ($)"].apply(lambda x: f"${x:.2f}" if pd.notnull(x) else "")

st.dataframe(filtered_df)
