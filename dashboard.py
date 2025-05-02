import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import pytz
from datetime import datetime
import psycopg2
from utils import load_data, detect_cluster_alerts, format_currency, generate_gpt_summary
from top10 import display_top10_charts

st.set_page_config(page_title="PulseReveal - Insider Trading Dashboard", layout="wide")
st.title("📊 PulseReveal - Insider Trading Dashboard")

# --- Detect and Store User Timezone ---
components.html(
    """
    <script>
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        window.parent.postMessage({ timezone: timezone }, "*");
    </script>
    """,
    height=0,
)

st.markdown("""
<script>
    window.addEventListener("message", (event) => {
        if (event.data.timezone) {
            window.parent.postMessage({ streamlit_timezone: event.data.timezone }, "*");
        }
    });
</script>
""", unsafe_allow_html=True)

# Store timezone in session_state
timezone = st.experimental_get_query_params().get("streamlit_timezone", [None])[0]
if timezone:
    st.session_state.timezone = timezone
elif "timezone" not in st.session_state:
    st.session_state.timezone = "UTC"

# --- Sidebar Filters ---
st.sidebar.header("Filters")
row_limit = st.sidebar.selectbox("Number of Transactions to Load", options=[100, 500, 1000], index=2)
start_date = st.sidebar.date_input("Start Date", value=datetime.utcnow().date())
end_date = st.sidebar.date_input("End Date", value=datetime.utcnow().date())
search_company = st.sidebar.text_input("Search Company")
search_insider = st.sidebar.text_input("Search Insider")

# --- Load Data ---
df = load_data(limit=row_limit)

# --- Filter Data ---
df["Reported Date"] = pd.to_datetime(df["Reported Date"])
df = df[(df["Reported Date"].dt.date >= start_date) & (df["Reported Date"].dt.date <= end_date)]
if search_company:
    df = df[df["Company"].str.contains(search_company, case=False)]
if search_insider:
    df = df[df["Insider"].str.contains(search_insider, case=False)]

# --- Convert UTC to Local Time ---
local_tz = pytz.timezone(st.session_state.timezone)
df["Reported Date"] = df["Reported Date"].dt.tz_localize("UTC").dt.tz_convert(local_tz)

# --- Volume Chart ---
st.subheader("📉 Transaction Volume by Day")
df_chart = df.groupby(df["Reported Date"].dt.date)["Amount ($)"].sum().reset_index()
st.line_chart(df_chart.rename(columns={"Reported Date": "Date", "Amount ($)": "Total Amount"}))

# --- Cluster Alerts ---
st.subheader("🧠 GPT Summary of Cluster Alerts")
cluster_alerts = detect_cluster_alerts(df)
for alert in cluster_alerts:
    with st.expander(f"📌 {alert['company']} — {alert['date']} — {format_currency(alert['total_value'])}"):
        st.markdown(f"**Insiders:** {', '.join(alert['insiders'])}")
        with st.spinner("Generating GPT Summary..."):
            summary = generate_gpt_summary(alert)
            st.success(summary)

# --- Top 10 Companies ---
st.subheader("🏢 Top 10 Companies by Total Dollar Value")
display_top10_charts(df)

# --- Transaction Table ---
st.subheader("📋 Transactions")
st.dataframe(df)
