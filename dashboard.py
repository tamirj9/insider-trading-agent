import streamlit as st
import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
import openai
import requests
import plotly.express as px

# ── ENVIRONMENT SETUP ──
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ── LOAD DATA ──
@st.cache_data(ttl=600)
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
        WHERE t.price_per_share > 0
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

# ── GPT SUMMARY ──
def get_summary(df):
    if df.empty: return "No data available to summarize."
    prompt = "Summarize insider trades:\n\n" + df[['Insider', 'Company', 'Date', 'Shares', 'Amount ($)']].head(10).to_csv(index=False)
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={"model": "mistralai/mixtral-8x7b", "messages": [{"role": "user", "content": prompt}]}
        )
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ GPT Summary failed: {e}"

# ── ALERTS ──
def send_alert(message):
    # Email
    try:
        import smtplib, ssl
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls(context=ssl.create_default_context())
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, EMAIL_USER, message)
        server.quit()
    except Exception as e:
        st.error(f"Email error: {e}")
    
    # Telegram
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={message}")
    except Exception as e:
        st.error(f"Telegram error: {e}")

# ── STREAMLIT UI ──
st.set_page_config("PulseReveal Dashboard", "📈", layout="wide")
st.title("📈 PulseReveal - Insider Trading Dashboard")
st.markdown("Stay updated on the latest insider trades.")

df = load_data()

# ── SIDEBAR FILTERS ──
st.sidebar.header("🔎 Filters")
start_date = st.sidebar.date_input("Start Date", df['Date'].min().date())
end_date = st.sidebar.date_input("End Date", df['Date'].max().date())
min_shares, max_shares = st.sidebar.slider("Shares Range", int(df['Shares'].min()), int(df['Shares'].max()), (int(df['Shares'].min()), int(df['Shares'].max())))
min_amt, max_amt = st.sidebar.slider("Amount Range ($)", int(df['Amount ($)'].min()), int(df['Amount ($)'].max()), (int(df['Amount ($)'].min()), int(df['Amount ($)'].max())))
search = st.sidebar.text_input("Search Insider or Company")
dedup_group = st.sidebar.selectbox("Group By", ["None", "Insider", "Company"])
max_rows = st.sidebar.selectbox("Show Top N Transactions", [100, 250, 500, 1000, 2000])

# ── APPLY FILTERS ──
filtered = df[
    (df['Date'] >= pd.Timestamp(start_date)) &
    (df['Date'] <= pd.Timestamp(end_date)) &
    (df['Shares'].between(min_shares, max_shares)) &
    (df['Amount ($)'].between(min_amt, max_amt))
]
if search:
    filtered = filtered[filtered['Insider'].str.contains(search, case=False) | filtered['Company'].str.contains(search, case=False)]

if dedup_group == "Insider":
    filtered = filtered.sort_values("Date", ascending=False).drop_duplicates("Insider")
elif dedup_group == "Company":
    filtered = filtered.sort_values("Date", ascending=False).drop_duplicates("Company")

filtered = filtered.head(max_rows)

# ── MAIN TABLE ──
st.subheader("📋 Insider Transactions")
if not filtered.empty:
    st.dataframe(filtered, use_container_width=True)
else:
    st.warning("No transactions match your filters.")

# ── CHARTS ──
st.subheader("📊 Visual Insights")
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(px.histogram(filtered, x="Date", y="Amount ($)", nbins=30, title="Transaction Volume Over Time"))
with col2:
    st.plotly_chart(px.bar(filtered.groupby("Company")['Amount ($)'].sum().nlargest(10).reset_index(), x="Company", y="Amount ($)", title="Top 10 Companies by Trade Value"))

# ── SUMMARY ──
st.subheader("🧠 GPT Summary")
summary = get_summary(filtered)
st.info(summary)

# ── CLUSTER ALERTS ──
clustered = filtered.groupby(["Company", "Date"])['Insider'].nunique().reset_index()
alerts = clustered[clustered['Insider'] >= 3]
if not alerts.empty:
    st.warning("🚨 Cluster Alerts:")
    st.dataframe(alerts)

# ── EMAIL & TELEGRAM ALERTS ──
if len(alerts) > 0:
    send_alert(f"🚨 {len(alerts)} cluster alerts found on PulseReveal")