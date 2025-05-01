import requests
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# --- GPT Summary ---
def generate_gpt_summary(text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": f"Summarize the following insider trading cluster:\n\n{text}"
            }
        ]
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        else:
            raise ValueError(f"Unexpected API response format: {result}")
    except Exception as e:
        print(f"⚠️ GPT Summary failed: {e}")
        return f"⚠️ GPT Summary failed: {e}"

# --- Cluster Alert Detection ---
def detect_cluster_alerts(df):
    alerts = []

    # Rename column if needed for grouping
    if "Trade Date" in df.columns:
        df_grouped = df.copy()
        df_grouped.rename(columns={"Trade Date": "Date"}, inplace=True)
    else:
        print("❌ 'Trade Date' not found in dataframe")
        return []

    grouped = df_grouped.groupby(["Date", "Company"])

    for (date, company), group in grouped:
        total_amount = group["Amount ($)"].sum()
        unique_insiders = group["Insider"].nunique()

        if total_amount >= 500_000 and unique_insiders >= 3:
            alerts.append({
                "Date": date,
                "Company": company,
                "Total Amount": total_amount,
                "Insiders": group["Insider"].unique().tolist(),
                "Count": len(group),
                "Trades": group.to_dict(orient="records")
            })

    return alerts
