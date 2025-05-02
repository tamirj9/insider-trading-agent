import sys
from alerts import send_email, send_telegram
from crawl_day_by_day.crawl_day_by_day import run as crawl_data

if __name__ == "__main__":
    try:
        crawl_data()
    except Exception as e:
        error_msg = f"❌ Daily crawler failed:\n\n{str(e)}"
        send_email("PulseReveal Crawler Error", error_msg)
        send_telegram(error_msg)
        sys.exit(1)