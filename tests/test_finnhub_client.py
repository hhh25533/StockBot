from unittest.mock import MagicMock, patch

import pytest
import requests

import finnhub_client


def _mock_response(payload):
    res = MagicMock()
    res.json.return_value = payload
    res.raise_for_status.return_value = None
    return res


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")


# ---- generate_us_response ----

def test_generate_response_up():
    out = finnhub_client.generate_us_response(
        {"symbol": "AAPL", "name": "Apple Inc", "o": 190.0, "c": 195.5, "pc": 190.0, "d": 5.5, "dp": 2.89})
    assert "AAPL Apple Inc" in out
    assert "190.00" in out
    assert "195.50" in out
    assert "2.89%" in out
    assert "📈" in out


def test_generate_response_down():
    out = finnhub_client.generate_us_response(
        {"symbol": "TSLA", "name": "Tesla Inc", "o": 250.0, "c": 240.0, "pc": 250.0, "d": -10.0, "dp": -4.0})
    assert "-4.00%" in out
    assert "📉" in out


def test_generate_response_flat_no_emoji():
    out = finnhub_client.generate_us_response(
        {"symbol": "FOO", "name": "", "o": 10.0, "c": 10.0, "pc": 10.0, "d": 0.0, "dp": 0.0})
    assert "📈" not in out and "📉" not in out
    assert "0.00%" in out


def test_generate_response_handles_none_name():
    # name 取不到時不應拋例外
    out = finnhub_client.generate_us_response(
        {"symbol": "AAPL", "name": None, "o": 1.0, "c": 1.0, "pc": 1.0, "d": 0.0, "dp": 0.0})
    assert out.startswith("AAPL")


# ---- get_us_stock_quote ----

def test_quote_missing_api_key(monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    assert finnhub_client.get_us_stock_quote("AAPL") == "尚未設定 FINNHUB_API_KEY"


def test_quote_empty_symbol(api_key):
    assert "請輸入美股代號" in finnhub_client.get_us_stock_quote("   ")


@patch("finnhub_client.requests.get")
def test_quote_valid_symbol(mock_get, api_key):
    mock_get.side_effect = [
        _mock_response({"c": 195.5, "o": 190.0, "pc": 190.0, "d": 5.5, "dp": 2.89}),
        _mock_response({"name": "Apple Inc"}),
    ]
    result = finnhub_client.get_us_stock_quote("aapl")
    assert isinstance(result, dict)
    assert result["symbol"] == "AAPL"  # 應被 upper()
    assert result["name"] == "Apple Inc"
    assert result["c"] == 195.5
    # 第一次呼叫 quote、第二次呼叫 profile2
    assert mock_get.call_count == 2

    quote_call, profile_call = mock_get.call_args_list
    # 打對 endpoint、帶對 symbol/token、且有 timeout（避免回歸時被拿掉）
    assert quote_call.args[0].endswith("/quote")
    assert quote_call.kwargs["params"] == {"symbol": "AAPL", "token": "test-key"}
    assert quote_call.kwargs["timeout"] == 10
    assert profile_call.args[0].endswith("/stock/profile2")
    assert profile_call.kwargs["params"] == {"symbol": "AAPL", "token": "test-key"}
    assert profile_call.kwargs["timeout"] == 10


@patch("finnhub_client.requests.get")
def test_quote_invalid_symbol_returns_error(mock_get, api_key):
    # finnhub 對無效代號所有數值回傳 0
    mock_get.return_value = _mock_response({"c": 0, "o": 0, "pc": 0, "d": 0, "dp": 0})
    result = finnhub_client.get_us_stock_quote("ZZZZZZ")
    assert result == "查無此代號，請確認輸入代號"
    # c==0 應提早 return，不會再打 profile2
    assert mock_get.call_count == 1


@patch("finnhub_client.requests.get")
def test_quote_request_exception_no_token_leak(mock_get, api_key):
    # 例外訊息含 token，回傳字串不應洩漏
    mock_get.side_effect = requests.exceptions.RequestException(
        "failed for url https://finnhub.io/api/v1/quote?symbol=AAPL&token=test-key")
    result = finnhub_client.get_us_stock_quote("AAPL")
    assert isinstance(result, str)
    assert "test-key" not in result
    assert "查詢" in result


@patch("finnhub_client.requests.get")
def test_quote_ok_but_profile_fails(mock_get, api_key):
    # 報價成功但公司名稱 API 失敗時，name 留空仍回傳報價
    mock_get.side_effect = [
        _mock_response({"c": 195.5, "o": 190.0, "pc": 190.0, "d": 5.5, "dp": 2.89}),
        requests.exceptions.RequestException("profile boom"),
    ]
    result = finnhub_client.get_us_stock_quote("AAPL")
    assert isinstance(result, dict)
    assert result["name"] == ""
    assert result["c"] == 195.5
