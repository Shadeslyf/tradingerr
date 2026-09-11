from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class Instrument(BaseModel):
    token: str
    symbol: str
    name: str
    expiry: Optional[str] = None
    strike: Optional[float] = None
    lotsize: str
    instrumenttype: str
    exch_seg: str
    tick_size: str

class BrokerClient(ABC):
    @abstractmethod
    def login(self) -> bool:
        pass

    @abstractmethod
    def get_instrument_master(self) -> List[Dict[str, Any]]:
        pass
