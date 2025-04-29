import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
import plotly.express as px
import openai

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Configure page
st.set_page_config(page_title="PulseReveal Dashboard", layout="wide")

# GPT summary generation
def generate_gpt_summary(data):
    try:
        openai.api_key = OPENROUTER_API_KEY
        if data.empty:
            return "No data to summarize."

        sample = data[["Date", "Insider", "Company", "Shares", "Amount ($)"]].head(20).to_string(index=False)
        prompt = f"Summarize key insider trading activity from the following table:\n\n{sample}"

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )

        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        else:
            return "⚠️ No summary generated — API returned no choices."

    except Exception as e:
        return f"⚠️ GPT Summary failed: {e}"

# Load data
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
        LIMIT 5000;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df.rename(columns={
        "insider_name": "Insider",
        "issuer_name": "Company",
        "transaction_date": "Date",
        "security_title": "Security",
        "shares": "Shares",
        "price_per_share": "Price ($)",
        "total_value": "Amount ($)"
    }, inplace=True)

    df["Date"] = pd.to_datetime(df["Date"])
    return df

# Sidebar Filters
st.sidebar.header("🔍 Filters")

df = load_data()

start_date = st.sidebar.date_input("Start Date", value=df["Date"].min().date())
end_date = st.sidebar.date_input("End Date", value=df["Date"].max().date())

shares_min, shares_max = st.sidebar.slider(
    "Shares Range", 0, int(df["Shares"].max()), (0, int(df["Shares"].max()))
)

amount_min, amount_max = st.sidebar.slider(
    "Amount Range ($)", 0, int(df["Amount ($)"].max()), (0, int(df["Amount ($)"].max()))
)

search_term = st.sidebar.text_input("Search Insider or Company")
group_by = st.sidebar.selectbox("Group By", ["None", "Insider", "Company"])

# Filter
filtered_df = df[
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date) &
    (df["Shares"] >= shares_min) & (df["Shares"] <= shares_max) &
    (df["Amount ($)"] >= amount_min) & (df["Amount ($)"] <= amount_max)
]

if search_term:
    filtered_df = filtered_df[
        filtered_df["Insider"].str.contains(search_term, case=False, na=False) |
        filtered_df["Company"].str.contains(search_term, case=False, na=False)
    ]

# Grouping
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

# Main display
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

# Chart
if not filtered_df.empty and "Date" in filtered_df.columns:
    fig = px.bar(
        filtered_df,
        x="Date" if group_by == "None" else group_by,
        y="Amount ($)",
        title="Transaction Volume",
        labels={"Amount ($)": "Amount ($)"},
        color="Company" if group_by == "None" else None
    )
    st.plotly_chart(fig, use_container_width=True)

# GPT Summary
st.subheader("🧠 GPT Summary")
summary = generate_gpt_summary(filtered_df)
st.info(summary)

# Data Table
st.subheader("📋 Transactions")
st.dataframe(filtered_df, use_container_width=True)

# Quick Stats
st.subheader("📊 Quick Stats")
col1, col2, col3 = st.columns(3)
col1.metric("Unique Insiders", df["Insider"].nunique())
col2.metric("Unique Companies", df["Company"].nunique())
col3.metric("Total Transactions", len(df))