import requests
import os
from dotenv import load_dotenv

load_dotenv()

def generate_gpt_summary(text):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "⚠️ GPT error: API key is missing"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": f"Summarize the following insider trading cluster:\n\n{text}"}
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        result = response.json()

        if "choices" in result and result["choices"]:
            return result["choices"][0]["message"]["content"]
        else:
            return f"⚠️ GPT Summary failed: Unexpected API response format.\n{result}"

    except Exception as e:
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