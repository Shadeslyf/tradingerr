import time
import datetime
from app.broker.angel_one import AngelOneBroker

broker = AngelOneBroker()
broker.login()

def on_tick(msg):
    items = [msg] if isinstance(msg, dict) else msg
    for item in items:
        if 'last_traded_price' in item and str(item.get('token', '')).strip() == '26000':
            ts = item.get('exchange_timestamp')
            pkt = item.get('packet_received_time')
            print(f"LTP: {item['last_traded_price']/100.0}")
            print(f"exchange_timestamp: {ts} -> {datetime.datetime.fromtimestamp(ts/1000.0) if ts else None}")
            print(f"packet_received_time: {pkt} -> {datetime.datetime.fromtimestamp(pkt/1000.0) if pkt else None}")
            import os; os._exit(0)

broker.init_websocket(on_tick_callback=on_tick)
time.sleep(2)
broker.subscribe_websocket("TEST", 1, [{"exchangeType": 1, "tokens": ["26000"]}])
time.sleep(10)
print("Timeout")
