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
