"""跨過 get_stock -> get_real_time_stock/odd -> handler 的接縫。

只 mock 外部邊界（requests.get 與 readCSV.read_csv），不 mock counting 內部函式，
避免像先前那樣因為 mock 掉受測對象而藏住 get_stock 回傳 str 的缺陷。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

import counting
import pythonbot

NOT_FOUND = "查無此代號，請確認輸入代號"

QUOTE = dict(b="99.0_", a="100.0_", z="101.00", o="98.00", y="100.00", c="2330", n="台積電")


class FakeTwse:
    """依 URL 回傳假的 TWSE 回應，並記錄被呼叫過的 URL。"""

    def __init__(self, info_records):
        self.info_records = info_records
        self.urls = []

    def get(self, url, *args, **kwargs):
        self.urls.append(url)
        res = MagicMock()
        if "getStock.jsp" in url:
            res.json.return_value = {"msgArray": [{"key": "tse_2330.tw"}]}
        else:
            res.json.return_value = {"msgArray": self.info_records}
        return res


@pytest.fixture
def twse(monkeypatch):
    fake = FakeTwse([QUOTE])
    monkeypatch.setattr(counting.requests, "get", fake.get)
    monkeypatch.setattr(counting.readCSV, "read_csv", lambda path, name: None)  # 名稱一律查無
    return fake


def _update(text, edited=False):
    update = MagicMock()
    reply = AsyncMock()
    msg = MagicMock(text=text, reply_text=reply)
    update.effective_message = msg
    update.message = None if edited else msg
    return update, reply


# ---- 查無代號：不得變成「查詢失敗」 ----

@pytest.mark.parametrize("text", ["/price TSMC", "/price 假股票", "/price"])
async def test_price_unknown_name_replies_not_found(twse, text):
    update, reply = _update(text)
    await pythonbot.quoted(update, MagicMock())
    reply.assert_awaited_once_with(NOT_FOUND)


async def test_odd_price_unknown_name_replies_not_found(twse):
    update, reply = _update("/odd_price TSMC")
    await pythonbot.odd_quoted(update, MagicMock())
    reply.assert_awaited_once_with(NOT_FOUND)


def test_real_functions_return_not_found_string_for_unknown_name(twse):
    assert counting.get_real_time_stock("TSMC") == NOT_FOUND
    assert counting.get_real_time_odd("TSMC") == NOT_FOUND
    assert twse.urls == []  # 查無代號時不應再打 TWSE


async def test_price_numeric_but_empty_key_reply_not_found(monkeypatch):
    monkeypatch.setattr(counting.requests, "get", lambda url, *a, **k: MagicMock(json=lambda: {"msgArray": []}))
    update, reply = _update("/price 9999")
    await pythonbot.quoted(update, MagicMock())
    reply.assert_awaited_once_with(NOT_FOUND)


async def test_price_empty_info_array_reply_not_found(monkeypatch):
    fake = FakeTwse([])
    monkeypatch.setattr(counting.requests, "get", fake.get)
    update, reply = _update("/price 2330")
    await pythonbot.quoted(update, MagicMock())
    reply.assert_awaited_once_with(NOT_FOUND)


# ---- 正常流程 ----

async def test_price_success_end_to_end(twse):
    update, reply = _update("/price 2330")
    await pythonbot.quoted(update, MagicMock())
    reply.assert_awaited_once_with("2330 台積電 開盤：98.00 \n當盤成交價 : 101.00 \t1.00% 📈 ")
    assert any("getStockInfo.jsp?ex_ch=tse_2330.tw" in u for u in twse.urls)


async def test_odd_price_success_has_prefix_and_uses_odd_endpoint(twse):
    update, reply = _update("/odd_price 2330")
    await pythonbot.odd_quoted(update, MagicMock())
    assert reply.await_args.args[0].startswith("零股\n2330 台積電")
    assert any("getOddInfo.jsp" in u for u in twse.urls)


async def test_price_double_space_is_stripped(twse):
    update, reply = _update("/price  2330")
    await pythonbot.quoted(update, MagicMock())
    assert reply.await_args.args[0].startswith("2330 台積電")


async def test_odd_price_double_space_is_stripped(twse):
    update, reply = _update("/odd_price  2330 ")
    await pythonbot.odd_quoted(update, MagicMock())
    assert reply.await_args.args[0].startswith("零股\n2330 台積電")


async def test_price_missing_buy_field_end_to_end(monkeypatch):
    fake = FakeTwse([{k: v for k, v in QUOTE.items() if k != "b"}])
    monkeypatch.setattr(counting.requests, "get", fake.get)
    update, reply = _update("/price 2330")
    await pythonbot.quoted(update, MagicMock())
    assert "101.00" in reply.await_args.args[0]


# ---- 零股：無法取得成交價時不加前綴 ----

async def test_odd_price_unavailable_has_no_prefix(monkeypatch):
    fake = FakeTwse([dict(c="2330", n="台積電", y="100.00")])
    monkeypatch.setattr(counting.requests, "get", fake.get)
    update, reply = _update("/odd_price 2330")
    await pythonbot.odd_quoted(update, MagicMock())
    reply.assert_awaited_once_with(counting.PRICE_UNAVAILABLE_MESSAGE)


# ---- 編輯訊息：update.message is None ----

async def test_edited_message_price_still_replies(twse):
    update, reply = _update("/price 2330", edited=True)
    await pythonbot.quoted(update, MagicMock())
    assert reply.await_args.args[0].startswith("2330 台積電")


async def test_edited_message_odd_price_still_replies(twse):
    update, reply = _update("/odd_price 2330", edited=True)
    await pythonbot.odd_quoted(update, MagicMock())
    assert reply.await_args.args[0].startswith("零股\n2330 台積電")


async def test_edited_message_failure_still_replies_failure_message(monkeypatch):
    monkeypatch.setattr(counting.requests, "get", MagicMock(side_effect=RuntimeError("net")))
    update, reply = _update("/price 2330", edited=True)
    await pythonbot.quoted(update, MagicMock())
    reply.assert_awaited_once_with(pythonbot.FAILURE_MESSAGE)


async def test_no_effective_message_does_not_raise(monkeypatch):
    monkeypatch.setattr(counting.requests, "get", MagicMock(side_effect=RuntimeError("net")))
    update = MagicMock()
    update.message = None
    update.effective_message = None
    await pythonbot.quoted(update, MagicMock())  # 不得拋出
