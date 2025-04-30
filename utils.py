import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch API key from env
API_KEY = os.getenv("OPENROUTER_API_KEY")

# GPT Model config
GPT_MODEL = "meta-llama/llama-2-70b-chat"
GPT_API_URL = "https://openrouter.ai/api/v1/chat/completions"

def generate_gpt_summary(text):
    if not API_KEY:
        return "⚠️ GPT Summary failed: No auth credentials found"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GPT_MODEL,
        "messages": [
            {
                "role": "user",
                "content": f"Summarize the following insider trading data:
\n\n{text}"
            }
        ]
    }

    try:
        response = requests.post(GPT_API_URL, headers=headers, json=data)
        result = response.json()
        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"]
        else:
            return f"⚠️ GPT Summary failed: {result}"
    except Exception as e:
        return f"⚠️ GPT Summary failed: {e}"

def detect_cluster_alerts(df):
    alerts = []
    grouped = df.groupby(["Date", "Company"])
    for (date, company), group in grouped:
        total_amount = group["Amount ($)"].sum()
        unique_insiders = group["Insider"].nunique()
        if total_amount >= 500000 and unique_insiders >= 3:
            alerts.append({
                "Date": date,
                "Company": company,
                "Total Amount": total_amount,
                "Insiders": group["Insider"].unique().tolist(),
                "Count": len(group)
            })
    return alerts
