from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    angel_api_key: str = Field(default="dummy_api_key")
    angel_client_id: str = Field(default="dummy_client_id")
    angel_password: str = Field(default="dummy_password")
    angel_totp: str = Field(default="dummy_totp")

    trading_mode: str = Field(default="PAPER")
    initial_capital: float = Field(default=300000.0)
    max_risk_per_trade: float = Field(default=0.005)
    max_daily_loss: float = Field(default=0.015)
    max_weekly_loss: float = Field(default=0.03)
    max_drawdown: float = Field(default=0.10)
    ai_min_confidence: float = Field(default=0.65)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
