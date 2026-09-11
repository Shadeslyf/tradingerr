from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database.models import MarketTick, OptionContract
from datetime import datetime

class MarketDataRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_tick(self, tick_data: Dict[str, Any]):
        tick = MarketTick(**tick_data)
        self.session.add(tick)
        self.session.commit()

    def save_ticks_bulk(self, ticks_data: List[Dict[str, Any]]):
        ticks = [MarketTick(**data) for data in ticks_data]
        self.session.add_all(ticks)
        self.session.commit()

    def get_ticks_since(self, since_timestamp: datetime) -> List[MarketTick]:
        return self.session.query(MarketTick).filter(MarketTick.timestamp >= since_timestamp).order_by(MarketTick.timestamp.asc()).all()

    def get_all_ticks(self) -> List[MarketTick]:
        return self.session.query(MarketTick).order_by(MarketTick.timestamp.asc()).all()

    def delete_ticks_before(self, before_timestamp: datetime):
        self.session.query(MarketTick).filter(MarketTick.timestamp < before_timestamp).delete()
        self.session.commit()

class OHLCVRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_ohlcv_bulk(self, ohlcv_data_list: List[Dict[str, Any]]):
        from app.database.models import OHLCV
        new_candles = []
        for data in ohlcv_data_list:
            new_candles.append(OHLCV(**data))
        if new_candles:
            self.session.add_all(new_candles)
            self.session.commit()

class OptionContractRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_contract(self, contract_data: Dict[str, Any]):
        # Check if exists to avoid unique constraint errors
        exists = self.session.query(OptionContract).filter_by(token=contract_data['token']).first()
        if not exists:
            contract = OptionContract(**contract_data)
            self.session.add(contract)
            self.session.commit()

    def save_contracts_bulk(self, contracts_data: List[Dict[str, Any]]):
        new_contracts = []
        for data in contracts_data:
            exists = self.session.query(OptionContract).filter_by(token=data['token']).first()
            if not exists:
                new_contracts.append(OptionContract(**data))
        if new_contracts:
            self.session.add_all(new_contracts)
            self.session.commit()

class TradeRepository:
    def __init__(self, session: Session):
        self.session = session
        from app.database.models import PaperTrade
        self.model = PaperTrade
        
    def create_trade(self, trade_data: Dict[str, Any]) -> int:
        trade = self.model(**trade_data)
        self.session.add(trade)
        self.session.commit()
        return trade.id
        
    def update_trade(self, trade_id: int, update_data: Dict[str, Any]):
        trade = self.session.query(self.model).filter_by(id=trade_id).first()
        if trade:
            for key, value in update_data.items():
                setattr(trade, key, value)
            self.session.commit()
            
    def get_open_trades(self):
        return self.session.query(self.model).filter_by(status='OPEN').all()
