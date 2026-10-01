import json
from types import SimpleNamespace

import pytest

import counting


def _stock(**fields):
    """模擬 TWSE msgArray：json -> SimpleNamespace，欄位缺漏就是真的沒有該屬性。"""
    return json.loads(json.dumps([fields]), object_hook=lambda d: SimpleNamespace(**d))


FULL = dict(b="99.0_", a="100.0_", z="101.00", o="98.00", y="100.00", c="2330", n="台積電", w="90.00", u="110.00")


def test_normal_up():
    out = counting.generate_response(_stock(**FULL))
    assert out == "2330 台積電 開盤：98.00 \n當盤成交價 : 101.00 \t1.00% 📈 "


def test_normal_down():
    out = counting.generate_response(_stock(**{**FULL, "z": "95.00"}))
    assert "-5.00%" in out
    assert "📉" in out


def test_flat_no_emoji():
    out = counting.generate_response(_stock(**{**FULL, "z": "100.00"}))
    assert "0.00%" in out
    assert "📈" not in out and "📉" not in out


def test_missing_buy_price_field_does_not_raise():
    """線上真實炸掉的 case：非交易時段 msgArray 沒有 b。"""
    data = {k: v for k, v in FULL.items() if k != "b"}
    out = counting.generate_response(_stock(**data))
    assert "101.00" in out


def test_missing_sale_price_field_does_not_raise():
    data = {k: v for k, v in FULL.items() if k != "a"}
    out = counting.generate_response(_stock(**data))
    assert "101.00" in out


def test_missing_real_time_price_returns_unavailable_message():
    data = {k: v for k, v in FULL.items() if k != "z"}
    assert counting.generate_response(_stock(**data)) == counting.PRICE_UNAVAILABLE_MESSAGE


def test_only_bare_record_returns_unavailable_message():
    assert counting.generate_response(_stock(c="2330", n="台積電")) == counting.PRICE_UNAVAILABLE_MESSAGE


def test_missing_yesterday_price_returns_unavailable_message():
    data = {k: v for k, v in FULL.items() if k != "y"}
    assert counting.generate_response(_stock(**data)) == counting.PRICE_UNAVAILABLE_MESSAGE


def test_zero_yesterday_price_returns_unavailable_message():
    assert counting.generate_response(_stock(**{**FULL, "y": "0"})) == counting.PRICE_UNAVAILABLE_MESSAGE


def test_missing_open_shows_dash():
    data = {k: v for k, v in FULL.items() if k != "o"}
    assert "開盤：- " in counting.generate_response(_stock(**data))


def test_buy_dash_falls_back_to_w():
    out = counting.generate_response(_stock(**{**FULL, "b": "-", "z": "-", "w": "103.00"}))
    assert "103.00" in out


def test_sale_dash_uses_limit_up_price_and_celebration():
    out = counting.generate_response(_stock(**{**FULL, "a": "-", "u": "110.00"}))
    assert "110.00" in out
    assert "🎊" in out and "📈" in out


def test_sale_dash_but_price_down_replaces_celebration_with_down_emoji():
    out = counting.generate_response(_stock(**{**FULL, "a": "-", "u": "95.00"}))
    assert "📉" in out
    assert "🎊" not in out


def test_z_dash_falls_back_to_first_sale_price():
    out = counting.generate_response(_stock(**{**FULL, "z": "-", "a": "102.50_103.00_"}))
    assert "102.50" in out


def test_z_dash_and_a_missing_returns_unavailable_message():
    data = {k: v for k, v in FULL.items() if k != "a"}
    data["z"] = "-"
    assert counting.generate_response(_stock(**data)) == counting.PRICE_UNAVAILABLE_MESSAGE


def test_missing_name_and_id_do_not_raise():
    data = {k: v for k, v in FULL.items() if k not in ("c", "n")}
    assert "101.00" in counting.generate_response(_stock(**data))


# ---- generate_tse_response ----

def test_tse_normal():
    out = counting.generate_tse_response(_stock(z="20100.00", y="20000.00", n="發行量加權股價指數"))
    assert out == "大盤 發行量加權股價指數 \n大盤指數 : 20100.00 \t0.50% 📈 "


def test_tse_down():
    out = counting.generate_tse_response(_stock(z="19900.00", y="20000.00", n="x"))
    assert "-0.50%" in out and "📉" in out


@pytest.mark.parametrize("missing", ["z", "y"])
def test_tse_missing_field_returns_unavailable_message(missing):
    data = {"z": "20100.00", "y": "20000.00", "n": "x"}
    del data[missing]
    assert counting.generate_tse_response(_stock(**data)) == counting.PRICE_UNAVAILABLE_MESSAGE


def test_tse_dash_price_returns_unavailable_message():
    assert counting.generate_tse_response(_stock(z="-", y="20000.00", n="x")) == counting.PRICE_UNAVAILABLE_MESSAGE


# ---- 0 價、空 list、查無代號常數 ----

def test_zero_real_time_price_returns_unavailable_message():
    assert counting.generate_response(_stock(**{**FULL, "z": "0.00"})) == counting.PRICE_UNAVAILABLE_MESSAGE


def test_tse_zero_price_returns_unavailable_message():
    assert counting.generate_tse_response(_stock(z="0.00", y="20000.00", n="x")) == counting.PRICE_UNAVAILABLE_MESSAGE


def test_empty_list_returns_unavailable_message():
    assert counting.generate_response([]) == counting.PRICE_UNAVAILABLE_MESSAGE


def test_tse_empty_list_returns_unavailable_message():
    assert counting.generate_tse_response([]) == counting.PRICE_UNAVAILABLE_MESSAGE
