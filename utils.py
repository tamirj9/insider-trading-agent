import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# === GPT SUMMARIZATION ===
def generate_gpt_summary(text):
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistralai/mistral-7b-instruct",  # ✅ Free, fast, and available
        "messages": [
            {
                "role": "user",
                "content": f"Summarize the following insider trading cluster data:\n\n{text}"
            }
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        result = response.json()

        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"]
        elif "error" in result:
            return f"⚠️ GPT Summary failed: {result['error'].get('message', 'Unknown error')}"
        else:
            return "⚠️ GPT Summary failed: Unexpected response format"

    except Exception as e:
        return f"⚠️ GPT Summary failed: {e}"

# === CLUSTER ALERT DETECTION ===
def detect_cluster_alerts(df):
    alerts = []
    grouped = df.groupby(["Date", "Company"])

    for (date, company), group in grouped:
        total_amount = group["Amount ($)"].sum()
        unique_insiders = group["Insider"].nunique()

        if total_amount > 500_000 and unique_insiders >= 3:
            alerts.append({
                "Date": date,
                "Company": company,
                "Total Amount": total_amount,
                "Insiders": group["Insider"].unique().tolist(),
                "Count": len(group)
            })

    return alerts