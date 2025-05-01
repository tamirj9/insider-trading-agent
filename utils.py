# utils.py
import os
import requests
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def generate_gpt_summary(text: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {
                "role": "user",
                "content": f"Summarize the following insider trading cluster in plain English:\n\n{text}"
            }
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        result = response.json()
        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"]
        else:
            print("⚠️ GPT response error:", result)
            return "⚠️ GPT Summary failed: Unexpected API response format."
    except Exception as e:
        print(f"⚠️ GPT Summary failed: {e}")
        return f"⚠️ GPT Summary failed: {e}"


def detect_cluster_alerts(df: pd.DataFrame):
    alerts = []
    grouped = df.groupby(["Date", "Company"])
    for (date, company), group in grouped:
        if group["Amount ($)"].sum() >= 500_000 and group["Insider"].nunique() >= 3:
            alerts.append({
                "Date": date,
                "Company": company,
                "Total Amount": group["Amount ($)"].sum(),
                "Insiders": group["Insider"].unique().tolist(),
                "Count": len(group)
            })
    return alerts