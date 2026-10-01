import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import counting
import pythonbot


def _update(text="/price 2330"):
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.effective_message = update.message
    return update


def _records(**fields):
    return json.loads(json.dumps([fields]), object_hook=lambda d: SimpleNamespace(**d))


GOOD = dict(b="99.0_", a="100.0_", z="101.00", o="98.00", y="100.00", c="2330", n="台積電")


def test_import_has_no_side_effects():
    """handler 要能被測試 import：import 不得建立 FileHandler 或啟動 polling。"""
    assert not [h for h in pythonbot.logger.handlers if isinstance(h, logging.FileHandler)]


# ---- quoted ----

async def test_quoted_string_result_replies_once_and_skips_generate_response(monkeypatch):
    monkeypatch.setattr(counting, "get_real_time_stock", lambda _id: "查無此代號，請確認輸入代號")
    generate = MagicMock()
    monkeypatch.setattr(counting, "generate_response", generate)
    update = _update()

    await pythonbot.quoted(update, MagicMock())

    update.message.reply_text.assert_awaited_once_with("查無此代號，請確認輸入代號")
    generate.assert_not_called()


async def test_quoted_success_replies_with_generated_response(monkeypatch):
    monkeypatch.setattr(counting, "get_real_time_stock", lambda _id: _records(**GOOD))
    update = _update()

    await pythonbot.quoted(update, MagicMock())

    update.message.reply_text.assert_awaited_once()
    assert "2330 台積電" in update.message.reply_text.await_args.args[0]


async def test_quoted_missing_buy_field_still_replies_without_failure(monkeypatch):
    data = {k: v for k, v in GOOD.items() if k != "b"}
    monkeypatch.setattr(counting, "get_real_time_stock", lambda _id: _records(**data))
    update = _update()

    await pythonbot.quoted(update, MagicMock())

    update.message.reply_text.assert_awaited_once()
    assert update.message.reply_text.await_args.args[0] != pythonbot.FAILURE_MESSAGE


async def test_quoted_passes_stock_id_from_message(monkeypatch):
    get = MagicMock(return_value="x")
    monkeypatch.setattr(counting, "get_real_time_stock", get)

    await pythonbot.quoted(_update("/price 2330"), MagicMock())

    get.assert_called_once_with("2330")


async def test_quoted_exception_still_replies_to_user(monkeypatch):
    def boom(_id):
        raise RuntimeError("network down")

    monkeypatch.setattr(counting, "get_real_time_stock", boom)
    update = _update()

    await pythonbot.quoted(update, MagicMock())

    update.message.reply_text.assert_awaited_once_with(pythonbot.FAILURE_MESSAGE)


async def test_failure_reply_error_is_swallowed(monkeypatch):
    monkeypatch.setattr(counting, "get_real_time_stock", MagicMock(side_effect=RuntimeError("x")))
    update = _update()
    update.message.reply_text = AsyncMock(side_effect=RuntimeError("telegram down"))

    await pythonbot.quoted(update, MagicMock())  # 不得拋出

    update.message.reply_text.assert_awaited_once()


# ---- odd_quoted ----

async def test_odd_quoted_string_result_replies_once_and_skips_generate_response(monkeypatch):
    monkeypatch.setattr(counting, "get_real_time_odd", lambda _id: "查無此代號，請確認輸入代號")
    generate = MagicMock()
    monkeypatch.setattr(counting, "generate_response", generate)
    update = _update("/odd_price 2330")

    await pythonbot.odd_quoted(update, MagicMock())

    update.message.reply_text.assert_awaited_once_with("查無此代號，請確認輸入代號")
    generate.assert_not_called()


async def test_odd_quoted_success_prefixes_odd_lot(monkeypatch):
    monkeypatch.setattr(counting, "get_real_time_odd", lambda _id: _records(**GOOD))
    update = _update("/odd_price 2330")

    await pythonbot.odd_quoted(update, MagicMock())

    update.message.reply_text.assert_awaited_once()
    assert update.message.reply_text.await_args.args[0].startswith("零股\n2330 台積電")


async def test_odd_quoted_exception_still_replies_to_user(monkeypatch):
    monkeypatch.setattr(counting, "get_real_time_odd", MagicMock(side_effect=RuntimeError("x")))
    update = _update("/odd_price 2330")

    await pythonbot.odd_quoted(update, MagicMock())

    update.message.reply_text.assert_awaited_once_with(pythonbot.FAILURE_MESSAGE)


# ---- tse ----

async def test_tse_success(monkeypatch):
    monkeypatch.setattr(counting, "get_real_time_tse", lambda: _records(z="20100.00", y="20000.00", n="大盤"))
    update = _update("/tse")

    await pythonbot.tse(update, MagicMock())

    update.message.reply_text.assert_awaited_once()
    assert "20100.00" in update.message.reply_text.await_args.args[0]


async def test_tse_missing_field_replies_without_raising(monkeypatch):
    monkeypatch.setattr(counting, "get_real_time_tse", lambda: _records(y="20000.00", n="大盤"))
    update = _update("/tse")

    await pythonbot.tse(update, MagicMock())

    update.message.reply_text.assert_awaited_once_with(counting.PRICE_UNAVAILABLE_MESSAGE)


async def test_tse_exception_still_replies_to_user(monkeypatch):
    monkeypatch.setattr(counting, "get_real_time_tse", MagicMock(side_effect=RuntimeError("x")))
    update = _update("/tse")

    await pythonbot.tse(update, MagicMock())

    update.message.reply_text.assert_awaited_once_with(pythonbot.FAILURE_MESSAGE)


# ---- us_price / update_csv / start ----

async def test_us_price_string_result_replies_once(monkeypatch):
    monkeypatch.setattr(pythonbot.finnhub_client, "get_us_stock_quote", lambda s: "錯誤")
    generate = MagicMock()
    monkeypatch.setattr(pythonbot.finnhub_client, "generate_us_response", generate)
    update = _update()
    context = MagicMock(args=["AAPL"])

    await pythonbot.us_price(update, context)

    update.message.reply_text.assert_awaited_once_with("錯誤")
    generate.assert_not_called()


async def test_us_price_exception_still_replies_to_user(monkeypatch):
    monkeypatch.setattr(pythonbot.finnhub_client, "get_us_stock_quote", MagicMock(side_effect=RuntimeError("x")))
    update = _update()

    await pythonbot.us_price(update, MagicMock(args=["AAPL"]))

    update.message.reply_text.assert_awaited_once_with(pythonbot.FAILURE_MESSAGE)


async def test_update_csv_success_and_failure(monkeypatch):
    monkeypatch.setattr(pythonbot.fetchCode, "update_codes", lambda: None)
    update = _update()
    await pythonbot.update_csv(update, MagicMock())
    update.message.reply_text.assert_awaited_once_with("更新完成")

    monkeypatch.setattr(pythonbot.fetchCode, "update_codes", MagicMock(side_effect=RuntimeError("x")))
    update = _update()
    await pythonbot.update_csv(update, MagicMock())
    update.message.reply_text.assert_awaited_once_with(pythonbot.FAILURE_MESSAGE)


async def test_start_failure_replies_to_user():
    update = _update("/start")
    context = MagicMock()
    context.bot.send_message = AsyncMock(side_effect=RuntimeError("x"))

    await pythonbot.start(update, context)

    update.message.reply_text.assert_awaited_once_with(pythonbot.START_FAILURE_MESSAGE)


# ---- main (fail-closed 啟動檢查) ----

def test_main_without_token_raises_before_building_app(monkeypatch):
    monkeypatch.delenv("TELEGRAM_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(pythonbot, "load_dotenv", lambda *_a, **_k: None)
    monkeypatch.setattr(pythonbot, "setup_logging", lambda: None)
    builder = MagicMock()
    monkeypatch.setattr(pythonbot, "ApplicationBuilder", builder)

    with pytest.raises(RuntimeError, match="TELEGRAM_ACCESS_TOKEN"):
        pythonbot.main()

    builder.assert_not_called()


def test_main_registers_all_handlers_and_polls(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ACCESS_TOKEN", "tok")
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.setattr(pythonbot, "load_dotenv", lambda *_a, **_k: None)
    monkeypatch.setattr(pythonbot, "setup_logging", lambda: None)
    builder = MagicMock()
    monkeypatch.setattr(pythonbot, "ApplicationBuilder", builder)
    app = builder.return_value.token.return_value.build.return_value

    pythonbot.main()  # 缺 FINNHUB_API_KEY 只警告，不終止

    builder.return_value.token.assert_called_once_with("tok")
    # PTB 會把指令名稱轉成小寫
    registered = {next(iter(c.args[0].commands)): c.args[0].callback for c in app.add_handler.call_args_list}
    assert registered == {
        "start": pythonbot.start,
        "price": pythonbot.quoted,
        "odd_price": pythonbot.odd_quoted,
        "tse": pythonbot.tse,
        "usprice": pythonbot.us_price,
        "updatecsv": pythonbot.update_csv,
    }
    app.run_polling.assert_called_once()
