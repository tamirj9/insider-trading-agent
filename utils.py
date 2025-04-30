import requests
import os
from dotenv import load_dotenv

load_dotenv()

def generate_gpt_summary(text):
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/llama-2-70b-chat",
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
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"⚠️ GPT Summary failed: {e}")
        return f"⚠️ GPT Summary failed: {e}"

def detect_cluster_alerts(df):
    alerts = []
    grouped = df.groupby(["Date", "Company"])
    for (date, company), group in grouped:
        if group["Amount ($)"].sum() > 1_000_000 and group["Insider"].nunique() > 2:
            alerts.append({
                "Date": date,
                "Company": company,
                "Total Amount": group["Amount ($)"].sum(),
                "Insiders": group["Insider"].unique().tolist(),
                "Count": len(group)
            })
    return alerts