import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connect to PostgreSQL
def connect_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Main cleaning and transfer function
def clean_and_transfer():
    conn = connect_db()
    cur = conn.cursor()

    print("🔄 Fetching raw transactions...")

    # Corrected column names
    query = """
    SELECT id, insider, issuer, transactiondate, transactioncode, securitytitle, shares, price
    FROM raw_transactions
    WHERE transactioncode IN ('P', 'S', 'M', 'A')
    """
    df = pd.read_sql_query(query, conn)

    print(f"📄 {len(df)} valid raw transactions found.")

    inserted = 0

    for idx, row in df.iterrows():
        insider_name = row['insider']
        issuer_name = row['issuer']
        transaction_date = row['transactiondate']
        transaction_code = row['transactioncode']
        security_title = row['securitytitle'] or 'Common Stock'
        shares = row['shares'] or 0
        price = row['price'] or 0
        filing_date = transaction_date  # Assume filing date same as transaction date

        if shares == 0:
            continue

        # 1. Get or insert issuer
        cur.execute("SELECT company_id FROM issuers WHERE company_name = %s", (issuer_name,))
        result = cur.fetchone()
        if result:
            company_id = result[0]
        else:
            cur.execute("INSERT INTO issuers (company_name) VALUES (%s) RETURNING company_id", (issuer_name,))
            company_id = cur.fetchone()[0]

        # 2. Get or insert insider
        cur.execute("SELECT insider_id FROM insiders WHERE name = %s AND company_id = %s", (insider_name, company_id))
        result = cur.fetchone()
        if result:
            insider_id = result[0]
        else:
            cur.execute(
                "INSERT INTO insiders (name, company_id, relationship) VALUES (%s, %s, %s) RETURNING insider_id",
                (insider_name, company_id, 'Unknown')
            )
            insider_id = cur.fetchone()[0]

        # 3. Map transaction code to type
        transaction_type = {
            'P': 'Buy',
            'S': 'Sell',
            'M': 'Option Exercise',
            'A': 'Award'
        }.get(transaction_code, 'Other')

        # 4. Insert into transactions
        cur.execute("""
            INSERT INTO transactions (
                insider_id, company_id, transaction_date, transaction_code, 
                security_title, transaction_type, shares, price_per_share, total_value, filing_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            insider_id, company_id, transaction_date, transaction_code,
            security_title, transaction_type, int(shares), float(price),
            float(shares) * float(price), filing_date
        ))

        inserted += 1

        # 🖨 Print progress every 50 inserted
        if inserted % 50 == 0:
            print(f"📊 Inserted {inserted} records...")

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Inserted {inserted} clean transactions into transactions table!")

if __name__ == "__main__":
    clean_and_transfer()