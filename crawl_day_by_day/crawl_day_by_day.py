import os
import time
import requests
import psycopg2
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
TARGET_DAY = datetime.now()           # automatic  date
TIMEOUT    = 10                       # seconds to wait on each request
DELAY_IDX  = 1.0                      # pause after fetching the index file
DELAY_FILE = 0.5                      # pause after parsing each filing

# ─────────────────────────────────────────────────────────────
# ENVIRONMENT & DATABASE SETUP
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
conn = None
cur = None

# ─────────────────────────────────────────────────────────────
# SEC-compliant HTTP session
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/113.0.0.0 Safari/537.36 "
                   "InsiderCrawler/1.0 (tamirjargalsaikhan@gmail.com)",
    "Accept":     "text/plain,application/xml,*/*;q=0.1",
})

BASE_URL = "https://www.sec.gov/Archives/edgar/daily-index/"

# ─────────────────────────────────────────────────────────────
def idx_url_for(day: datetime) -> str:
    quarter = (day.month - 1)//3 + 1
    ds      = day.strftime("%Y%m%d")
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
        # Fetch the raw .txt filing
        txt_url = f"https://www.sec.gov/Archives/{path}"
        r = session.get(txt_url, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        content = r.text

        # Extract the XML block starting at <ownershipDocument>
        start_tag = '<ownershipDocument'
        end_tag = '</ownershipDocument>'
        start = content.find(start_tag)
        end   = content.find(end_tag, start)
        if start == -1 or end == -1:
            return None
        xml_str = content[start:end + len(end_tag)]

        root = ET.fromstring(xml_str)

        # Extract issuer and insider
        issuer_el  = root.find('.//issuer/issuerName')
        insider_el = root.find('.//reportingOwner//reportingOwnerId//rptOwnerName')
        if issuer_el is None or insider_el is None:
            return None
        issuer  = issuer_el.text.strip()
        insider = insider_el.text.strip()

        rows = []

        # Non-derivative transactions
        for nd in root.findall('.//nonDerivativeTable//nonDerivativeTransaction'):
            dt = nd.find('transactionDate/value')
            cd = nd.find('transactionCoding/transactionCode')
            st = nd.find('securityTitle/value')
            sh = nd.find('transactionAmounts/transactionShares/value')
            pr = nd.find('transactionAmounts/transactionPricePerShare/value')
            if not (dt is not None and cd is not None and sh is not None and pr is not None):
                continue
                
            # Fix date format by properly handling timezone
            transaction_date_text = dt.text.strip()
            # If it includes timezone info (something like "2025-04-24-05:00")
            if transaction_date_text.count('-') > 2:
                # Extract just the date portion (YYYY-MM-DD)
                transaction_date = '-'.join(transaction_date_text.split('-')[:3])
            else:
                # It's already in the right format
                transaction_date = transaction_date_text
            
            rows.append({
                'issuer':           issuer,
                'insider':          insider,
                'transactiondate':  transaction_date,
                'transactioncode':  cd.text.strip(),
                'securitytitle':    st.text.strip() if st is not None else None,
                'type':             'Non-Derivative',
                'shares':           float(sh.text.strip()),
                'price':            float(pr.text.strip()),
            })

        # Derivative transactions
        for d in root.findall('.//derivativeTable//derivativeTransaction'):
            dt = d.find('transactionDate/value')
            cd = d.find('transactionCoding/transactionCode')
            st = d.find('securityTitle/value')
            
            # Fix deprecation warnings with proper "is not None" checks
            sh_elem1 = d.find('transactionAmounts/transactionShares/value')
            sh_elem2 = d.find('underlyingSecurity/underlyingSecurityShares/value')
            sh = sh_elem1 if sh_elem1 is not None else sh_elem2
            
            pr_elem1 = d.find('transactionAmounts/transactionPricePerShare/value')
            pr_elem2 = d.find('exercisePrice/value')
            pr = pr_elem1 if pr_elem1 is not None else pr_elem2
            
            if not (dt is not None and cd is not None and sh is not None and pr is not None):
                continue
                
            # Fix date format by properly handling timezone
            transaction_date_text = dt.text.strip()
            # If it includes timezone info (something like "2025-04-24-05:00")
            if transaction_date_text.count('-') > 2:
                # Extract just the date portion (YYYY-MM-DD)
                transaction_date = '-'.join(transaction_date_text.split('-')[:3])
            else:
                # It's already in the right format
                transaction_date = transaction_date_text
            
            rows.append({
                'issuer':           issuer,
                'insider':          insider,
                'transactiondate':  transaction_date,
                'transactioncode':  cd.text.strip(),
                'securitytitle':    st.text.strip() if st is not None else None,
                'type':             'Derivative',
                'shares':           float(sh.text.strip()),
                'price':            float(pr.text.strip()),
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

if __name__ == '__main__':
    try:
        connect_db()
        print(f"── Crawling {TARGET_DAY.strftime('%Y-%m-%d')} (raw import) ──")
        idxs = fetch_index(TARGET_DAY)
        if not idxs:
            print(f"⚠️ No index for {TARGET_DAY.date()}")
        else:
            print(f"📄 {len(idxs)} filings found for {TARGET_DAY.date()}")
            inserted = 0
            for path in idxs:
                df = parse_filing(path)
                if df is not None:
                    upsert_trades(df)
                    print(f"✅ inserted {len(df)} rows from {path}")
                    inserted += 1
                else:
                    print(f"▶️ no transactions in {path}")
                time.sleep(DELAY_FILE)
            print(f"🏁 Imported {inserted} filings raw for {TARGET_DAY.date()}")
    except Exception as e:
        print(f"⚠️ Fatal error: {e}")
    finally:
        if conn is not None:
            if cur is not None:
                cur.close()
            conn.close()
            print("✅ Database connection closed")