import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Connect to the database
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ─────────────────────────────────────────────────────────────

def clean_and_transfer():
    print("🔄 Fetching raw transactions...")
    query = """
        SELECT id, insider, issuer, transactiondate, transactioncode, securitytitle, shares, price
        FROM raw_transactions
        WHERE transactioncode IN ('P', 'S', 'M', 'A')
    """
    df = pd.read_sql_query(query, conn)
    print(f"📄 {len(df)} valid raw transactions found.")

    if df.empty:
        print("⚠️ No valid transactions to process.")
        return

    processed = 0

    for _, row in df.iterrows():
        insider_name = row['insider']
        issuer_name = row['issuer']
        transaction_date = row['transactiondate']
        transaction_code = row['transactioncode']
        security_title = row['securitytitle']
        shares = row['shares']
        price = row['price']

        # Insert issuer
        cur.execute("SELECT company_id FROM issuers WHERE company_name = %s", (issuer_name,))
        result = cur.fetchone()
        if result:
            company_id = result[0]
        else:
            cur.execute("INSERT INTO issuers (company_name) VALUES (%s) RETURNING company_id", (issuer_name,))
            company_id = cur.fetchone()[0]

        # Insert insider
        cur.execute("SELECT insider_id FROM insiders WHERE name = %s AND company_id = %s", (insider_name, company_id))
        result = cur.fetchone()
        if result:
            insider_id = result[0]
        else:
            cur.execute("INSERT INTO insiders (name, company_id, relationship) VALUES (%s, %s, %s) RETURNING insider_id", (insider_name, company_id, "Unknown"))
            insider_id = cur.fetchone()[0]

        # Insert transaction
        cur.execute("""
            INSERT INTO transactions (
                insider_id, company_id, transaction_date, transaction_code,
                security_title, transaction_type, shares, price_per_share, total_value, filing_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            insider_id, company_id, transaction_date, transaction_code,
            security_title, "Purchase/Sale/Other", shares, price, shares * price
        ))

        # Mark as processed
        cur.execute("DELETE FROM raw_transactions WHERE id = %s", (row['id'],))

        processed += 1

    conn.commit()
    print(f"✅ {processed} transactions cleaned and transferred.")

    if processed > 0:
        send_email(processed)

# ─────────────────────────────────────────────────────────────

def send_email(count):
    subject = f"✅ Insider Trades Processed: {count} New Transactions"
    body = f"Today, {count} insider trades were cleaned and added to the database successfully.\n\n- Your automated insider trading crawler"

    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("📧 Notification email sent!")
    except Exception as e:
        print(f"⚠️ Failed to send email: {e}")

# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    clean_and_transfer()
    cur.close()
    conn.close()
