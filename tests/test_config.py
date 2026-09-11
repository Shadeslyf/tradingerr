import pytest
from app.config.settings import Settings

def test_default_settings():
    settings = Settings()
    assert settings.trading_mode == "PAPER"
    assert settings.initial_capital == 300000.0
    assert settings.angel_api_key == "dummy_api_key"
