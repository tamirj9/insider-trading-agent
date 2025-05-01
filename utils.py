# utils.py (updated to cache GPT summaries and reduce unnecessary API calls)

import requests
import os
import hashlib
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

CACHE_DIR = ".gpt_cache"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

# Ensure cache folder exists
os.makedirs(CACHE_DIR, exist_ok=True)

def _get_cache_filename(text: str) -> str:
    hash_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"summary_{hash_digest}.json")

def generate_gpt_summary(text: str) -> str:
    if not OPENROUTER_API_KEY:
        return "⚠️ GPT error: API key not set"

    cache_path = _get_cache_filename(text)
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            return json.load(f)["summary"]

    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": f"Summarize the following insider trading cluster:\n\n{text}"}
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=HEADERS, json=payload)
        result = response.json()

        if "choices" not in result:
            raise ValueError(f"Unexpected API response format. {result}")

        summary = result["choices"][0]["message"]["content"]

        # Save to cache
        with open(cache_path, 'w') as f:
            json.dump({"summary": summary}, f)

        return summary

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
                "Count": len(group),
                "Text": group.to_string(index=False)
            })
    return alerts