import requests
import os
from dotenv import load_dotenv

load_dotenv()

def generate_gpt_summary(text: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "⚠️ GPT API key is missing."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a financial analyst. Summarize the following insider trading activity in plain English."},
            {"role": "user", "content": text}
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        result = response.json()

        # Handle structured errors
        if "error" in result:
            print("⚠️ GPT API error:", result["error"])
            return f"⚠️ GPT error: {result['error'].get('message', 'Unknown error')}"

        # Expected output format
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            print("⚠️ Unexpected API response:", result)
            return "⚠️ GPT Summary failed: Unexpected response format."
    except Exception as e:
        print("⚠️ Exception during GPT summary:", str(e))
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
