import pytest
from unittest.mock import patch, MagicMock
from app.broker.angel_one import AngelOneBroker

@patch('app.broker.angel_one.requests.get')
def test_get_instrument_master(mock_get):
    # Mock the response from requests.get
    mock_response = MagicMock()
    mock_response.json.return_value = [{"token": "26000", "symbol": "Nifty 50"}]
    mock_get.return_value = mock_response

    broker = AngelOneBroker()
    instruments = broker.get_instrument_master()

    assert len(instruments) == 1
    assert instruments[0]['token'] == '26000'
    mock_get.assert_called_once()

def test_login_dummy_credentials():
    # Because client_id is "dummy_client_id" by default, it should return False
    broker = AngelOneBroker()
    assert broker.client_id == "dummy_client_id"
    success = broker.login()
    assert success is False
