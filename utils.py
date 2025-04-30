# utils.py

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def generate_gpt_summary(text):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "⚠️ GPT Summary failed: No API key found in environment."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": f"Summarize the following insider trading cluster:

{text}"
            }
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        result = response.json()
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        else:
            return f"⚠️ GPT Summary failed: {result}"
    except Exception as e:
        return f"⚠️ GPT Summary failed: {e}"

def detect_cluster_alerts(df):
    alerts = []
    grouped = df.groupby(["Date", "Company"])
    for (date, company), group in grouped:
        if group["Amount ($)"].sum() > 500_000 and group["Insider"].nunique() >= 3:
            alerts.append({
                "Date": date,
                "Company": company,
                "Total Amount": group["Amount ($)"].sum(),
                "Insiders": group["Insider"].unique().tolist(),
                "Count": len(group)
            })
    return alerts