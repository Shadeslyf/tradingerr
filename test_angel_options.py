import pyotp
from SmartApi import SmartConnect
from app.config.settings import settings

smart_api = SmartConnect(api_key=settings.angel_api_key)
totp = pyotp.TOTP(settings.angel_totp).now()
res = smart_api.generateSession(settings.angel_client_id, settings.angel_password, totp)
if res['status']:
    print("Login success")
    # try getting market data for NSE Nifty 50
    md = smart_api.getMarketData("LTP", {"NSE": ["26000"]})
    print(md)
else:
    print("Login failed", res)
