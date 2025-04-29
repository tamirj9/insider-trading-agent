import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email settings
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Function to send an email
def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_USER  # Sending to self, or could add more recipients
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())
        server.quit()
        print(f"✅ Email alert sent!")
    except Exception as e:
        print(f"⚠️ Email sending failed: {e}")

# Function to send a Telegram message
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            print(f"✅ Telegram alert sent!")
        else:
            print(f"⚠️ Telegram send error: {r.text}")
    except Exception as e:
        print(f"⚠️ Telegram sending failed: {e}")

# Combined function for alerts
def send_cluster_alert(summary_text, is_test=False):
    subject = "🚨 PulseReveal Cluster Alert"
    body = summary_text

    if not is_test:
        send_email(subject, body)
        send_telegram(body)
    else:
        print("[Test Mode] 🚨 Cluster alert simulated.")