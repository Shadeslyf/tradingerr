import json
import urllib.request
import pyotp
from SmartApi import SmartConnect
from loguru import logger
from typing import List, Dict, Any

from app.config.settings import settings
from app.broker.base import BrokerClient

class AngelOneBroker(BrokerClient):
    def __init__(self):
        self.api_key = settings.angel_api_key
        self.client_id = settings.angel_client_id
        self.password = settings.angel_password
        self.totp_secret = settings.angel_totp
        self.smart_api = SmartConnect(api_key=self.api_key)
        self.auth_token = None
        self.feed_token = None
        self.refresh_token = None
        self.instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

    def login(self) -> bool:
        logger.info(f"Attempting login for client ID: {self.client_id}")
        if self.client_id == "dummy_client_id":
            logger.warning("Dummy credentials used. Skipping actual login.")
            return False

        try:
            totp = pyotp.TOTP(self.totp_secret).now()
        except Exception as e:
            logger.error(f"Failed to generate TOTP: {e}")
            return False

        try:
            data = self.smart_api.generateSession(self.client_id, self.password, totp)
            if data['status']:
                self.auth_token = data['data']['jwtToken']
                self.refresh_token = data['data']['refreshToken']
                self.feed_token = self.smart_api.getfeedToken()
                logger.info("Successfully logged into Angel One.")
                return True
            else:
                logger.error(f"Login failed: {data}")
                return False
        except Exception as e:
            logger.error(f"Login exception: {e}")
            return False

    def get_instrument_master(self) -> List[Dict[str, Any]]:
        logger.info(f"Fetching instrument master from {self.instrument_url}")
        try:
            import requests
            response = requests.get(self.instrument_url, timeout=30)
            response.raise_for_status()
            instrument_list = response.json()
            logger.info(f"Successfully fetched {len(instrument_list)} instruments.")
            return instrument_list
        except Exception as e:
            logger.error(f"Failed to fetch instrument master: {e}")
            return []

    def get_candle_data(self, exchange: str, symboltoken: str, interval: str, fromdate: str, todate: str) -> List[Dict[str, Any]]:
        """
        Fetch historical candle data.
        interval: ONE_MINUTE, THREE_MINUTE, FIVE_MINUTE, etc.
        fromdate/todate format: 'YYYY-MM-DD HH:MM'
        """
        if not self.auth_token:
            logger.error("Not logged in. Call login() first.")
            return []
            
        historicParam = {
            "exchange": exchange,
            "symboltoken": symboltoken,
            "interval": interval,
            "fromdate": fromdate,
            "todate": todate
        }
        
        try:
            response = self.smart_api.getCandleData(historicParam)
            if response and response.get('status'):
                return response.get('data', [])
            else:
                logger.error(f"Failed to fetch candle data: {response}")
                return []
        except Exception as e:
            logger.error(f"Exception fetching candle data: {e}")
            return []

    # Implement abstract methods
    def get_quote(self, symbol: str, token: str) -> Dict[str, Any]:
        return {}
    def place_order(self, symbol: str, token: str, action: str, quantity: int, price: float = 0.0, order_type: str = 'MARKET') -> str:
        return "dummy_id"
    def cancel_order(self, order_id: str) -> bool:
        return True
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        return {}
    def get_positions(self) -> List[Dict[str, Any]]:
        return []
