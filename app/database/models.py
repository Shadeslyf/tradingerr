from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config.settings import settings

Base = declarative_base()

class MarketTick(Base):
    __tablename__ = 'market_ticks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, index=True, nullable=False)
    symbol = Column(String(50), index=True, nullable=False)
    token = Column(String(20), index=True, nullable=False)
    exchange = Column(String(10), nullable=False)
    ltp = Column(Float, nullable=False)
    volume = Column(BigInteger, default=0)
    open_interest = Column(BigInteger, default=0)
    bid = Column(Float, default=0.0)
    ask = Column(Float, default=0.0)

class OHLCV(Base):
    __tablename__ = 'ohlcv'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, index=True, nullable=False)
    symbol = Column(String(50), index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, default=0)
    open_interest = Column(BigInteger, default=0)

class OptionContract(Base):
    __tablename__ = 'option_contracts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    underlying = Column(String(50), index=True, nullable=False)
    expiry = Column(DateTime, index=True, nullable=False)
    strike = Column(Float, index=True, nullable=False)
    option_type = Column(String(2), nullable=False) # CE or PE
    symbol = Column(String(50), unique=True, nullable=False)
    token = Column(String(20), unique=True, nullable=False)
    lot_size = Column(Integer, nullable=False)

class PaperTrade(Base):
    __tablename__ = 'paper_trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(50), index=True, nullable=True) # Used to group multi-leg trades
    action = Column(String(10), nullable=False, default='BUY') # BUY or SELL
    symbol = Column(String(50), index=True, nullable=False)
    token = Column(String(20), nullable=False)
    option_type = Column(String(2), nullable=False) # CE or PE
    entry_time = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=50)
    exit_time = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    status = Column(String(20), default='OPEN') # OPEN, CLOSED
    exit_reason = Column(String(50), nullable=True) # SL, TP, EOD, SIGNAL
    
# Initialize engine and session factory
engine = create_engine(settings.db_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
