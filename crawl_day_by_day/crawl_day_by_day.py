# ... [keep all your imports and configuration as is] ...

def run(target_day: datetime = datetime.now()):
    global TARGET_DAY
    TARGET_DAY = target_day
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
                    print(f"✅ Inserted {len(df)} rows from {path}")
                    inserted += 1
                else:
                    print(f"▶️ No transactions in {path}")
                time.sleep(DELAY_FILE)
            print(f"🏁 Imported {inserted} filings for {TARGET_DAY.date()}")
    except Exception as e:
        print(f"⚠️ Fatal error: {e}")
    finally:
        if conn:
            if cur:
                cur.close()
            conn.close()
            print("✅ Database connection closed")

    # ─── TRIGGER CLEAN TRANSFER ───
    try:
        print("🔄 Running clean transfer after crawling...")
        subprocess.run(["python3", "clean_transfer/clean_transfer.py"], check=True)
        print("✅ Clean transfer finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Clean transfer subprocess error: {e}")
    except Exception as e:
        print(f"⚠️ Unexpected clean transfer error: {e}")


if __name__ == '__main__':
    run()