# cluster_alerts.py
import psycopg2
import os
import pandas as pd
from dotenv import load_dotenv
from gpt_summary import generate_summary
from send_email import send_email
from send_telegram import send_telegram

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Alert thresholds
CLUSTER_WINDOW_DAYS = 5
MIN_CLUSTER_SIZE = 3
MIN_ALERT_AMOUNT = 500000


def fetch_recent_trades():
    conn = psycopg2.connect(DATABASE_URL)
    query = """
        SELECT c.company_name, i.name AS insider_name, t.total_value, t.transaction_date
        FROM transactions t
        JOIN insiders i ON t.insider_id = i.insider_id
        JOIN issuers c ON t.company_id = c.company_id
        WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '%s day'
        ORDER BY t.transaction_date DESC
    """
    df = pd.read_sql_query(query, conn, params=(CLUSTER_WINDOW_DAYS,))
    conn.close()
    return df


def detect_clusters(df):
    alerts = []
    grouped = df.groupby("company_name")
    for company, group in grouped:
        if len(group) >= MIN_CLUSTER_SIZE and group['total_value'].sum() >= MIN_ALERT_AMOUNT:
            alerts.append(group)
    return alerts


def run_cluster_alerts():
    df = fetch_recent_trades()
    clusters = detect_clusters(df)

    for group in clusters:
        company = group['company_name'].iloc[0]
        summary = generate_summary(group)

        message = f"🚨 Cluster Buy Alert for {company}\n\n{summary}"
        send_email("Cluster Buy Alert", message)
        send_telegram(message)


if __name__ == "__main__":
    run_cluster_alerts()
