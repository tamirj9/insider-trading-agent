import os
import time
import requests
import psycopg2
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv
import subprocess

# ─── CONFIGURATION ───
TARGET_DAY = datetime.now()
TIMEOUT = 10
DELAY_IDX = 1.0
DELAY_FILE = 0.5

# ─── ENVIRONMENT SETUP ───
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
conn = None
cur = None

# ─── HTTP SESSION ───
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/113.0.0.0 Safari/537.36 "
                  "InsiderCrawler/1.0 (tamirjargalsaikhan@gmail.com)",
    "Accept": "text/plain,application/xml,*/*;q=0.1",
})

BASE_URL = "https://www.sec.gov/Archives/edgar/daily-index/"

# ─── FUNCTIONS ───
def idx_url_for(day: datetime) -> str:
    quarter = (day.month - 1)//3 + 1
    ds = day.strftime("%Y%m%d")
    return f"{BASE_URL}{day.year}/QTR{quarter}/form.{ds}.idx"

def fetch_index(day: datetime) -> list[str]:
    url = idx_url_for(day)
    try:
        r = session.get(url, timeout=TIMEOUT)
    except Exception as e:
        print(f"⚠️ [{day.date()}] idx fetch error: {e}")
        return []
    if r.status_code != 200:
        print(f"⚠️ [{day.date()}] idx status {r.status_code}")
        return []
    time.sleep(DELAY_IDX)
    return [
        line.split()[-1]
        for line in r.text.splitlines()
        if line.strip().startswith("4 ") and line.strip().endswith(".txt")
    ]

def parse_filing(path: str) -> pd.DataFrame | None:
    try:
        txt_url = f"https://www.sec.gov/Archives/{path}"
        r = session.get(txt_url, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        content = r.text

        start_tag = '<ownershipDocument'
        end_tag = '</ownershipDocument>'
        start = content.find(start_tag)
        end = content.find(end_tag, start)
        if start == -1 or end == -1:
            return None
        xml_str = content[start:end + len(end_tag)]

        root = ET.fromstring(xml_str)

        issuer_el = root.find('.//issuer/issuerName')
        insider_el = root.find('.//reportingOwner//reportingOwnerId//rptOwnerName')
        if issuer_el is None or insider_el is None:
            return None
        issuer = issuer_el.text.strip()
        insider = insider_el.text.strip()

        rows = []

        for nd in root.findall('.//nonDerivativeTable//nonDerivativeTransaction'):
            dt = nd.find('transactionDate/value')
            cd = nd.find('transactionCoding/transactionCode')
            st = nd.find('securityTitle/value')
            sh = nd.find('transactionAmounts/transactionShares/value')
            pr = nd.find('transactionAmounts/transactionPricePerShare/value')
            if not (dt and cd and sh and pr):
                continue
            transaction_date = dt.text.strip().split('T')[0]
            rows.append({
                'issuer': issuer,
                'insider': insider,
                'transactiondate': transaction_date,
                'transactioncode': cd.text.strip(),
                'securitytitle': st.text.strip() if st is not None else None,
                'type': 'Non-Derivative',
                'shares': float(sh.text.strip()),
                'price': float(pr.text.strip()),
            })

        for d in root.findall('.//derivativeTable//derivativeTransaction'):
            dt = d.find('transactionDate/value')
            cd = d.find('transactionCoding/transactionCode')
            st = d.find('securityTitle/value')
            sh_elem1 = d.find('transactionAmounts/transactionShares/value')
            sh_elem2 = d.find('underlyingSecurity/underlyingSecurityShares/value')
            sh = sh_elem1 if sh_elem1 is not None else sh_elem2
            pr_elem1 = d.find('transactionAmounts/transactionPricePerShare/value')
            pr_elem2 = d.find('exercisePrice/value')
            pr = pr_elem1 if pr_elem1 is not None else pr_elem2
            if not (dt and cd and sh and pr):
                continue
            transaction_date = dt.text.strip().split('T')[0]
            rows.append({
                'issuer': issuer,
                'insider': insider,
                'transactiondate': transaction_date,
                'transactioncode': cd.text.strip(),
                'securitytitle': st.text.strip() if st is not None else None,
                'type': 'Derivative',
                'shares': float(sh.text.strip()),
                'price': float(pr.text.strip()),
            })

        if not rows:
            return None
        return pd.DataFrame(rows)

    except Exception as e:
        print(f"⚠️ parse error {path}: {e}")
        return None

def upsert_trades(df: pd.DataFrame):
    try:
        for _, row in df.iterrows():
            cur.execute(
                "INSERT INTO raw_transactions (issuer, insider, transactiondate, transactioncode, securitytitle, type, shares, price) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (row['issuer'], row['insider'], row['transactiondate'], row['transactioncode'], row['securitytitle'], row['type'], row['shares'], row['price'])
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Database error: {e}")
        raise

def connect_db():
    global conn, cur
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("✅ Connected to database successfully")
    except Exception as e:
        print(f"⚠️ Database connection error: {e}")
        raise

def run(target_day: datetime = datetime.now()):
    connect_db()
    print(f"── Crawling {target_day.strftime('%Y-%m-%d')} (raw import) ──")
    idxs = fetch_index(target_day)
    if not idxs:
        print(f"⚠️ No index for {target_day.date()}")
    else:
        print(f"📄 {len(idxs)} filings found for {target_day.date()}")
        inserted = 0
        for path in idxs:
            df = parse_filing(path)
            if df is not None:
                upsert_trades(df)
                print(f"✅ Inserted {len(df)} rows from {path}")
                inserted += 1
            else:
                print(f"▶️ No transactions in {path}")
            time.sleep(DELAY_FILE)
        print(f"🏋️ Imported {inserted} filings for {target_day.date()}")
    if conn:
        if cur:
            cur.close()
        conn.close()
        print("✅ Database connection closed")

    try:
        print("🔄 Running clean transfer after crawling...")
        subprocess.run(["python3", "clean_transfer/clean_transfer.py"], check=True)
        print("✅ Clean transfer finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Clean transfer subprocess error: {e}")
    except Exception as e:
        print(f"⚠️ Unexpected clean transfer error: {e}")