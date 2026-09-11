import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.monitoring.logging import setup_logging
from app.data.ingestion.collector import MarketDataCollector

def main():
    setup_logging()
    collector = MarketDataCollector()
    collector.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Collector stopped.")

if __name__ == "__main__":
    main()
