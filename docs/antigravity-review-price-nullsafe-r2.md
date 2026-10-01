# Antigravity 複驗：price-nullsafe-r2
- date: 2026-10-01 08:22
- base: e054a08886bafd7b0fc618cfab4ac9a29c318aec
- head: e95182b50910619b1dbb921bb0fd4275d7c1cab8
- reviewer: antigravity-cli 1.2.14
- conversation: b16620b6-bd13-40ba-93a3-d5046332c68a

## 缺陷

[MAJOR] [src/counting.py:94-98](file:///Users/davidtin/StockBot/src/counting.py#L94-L98) — 當股票暫停交易或完全無買賣盤撮合時，雙邊為空判定使暫停交易個股被誤報為 +10.00% 漲停並附帶慶祝符號
- 證據：
  [src/counting.py:94-98](file:///Users/davidtin/StockBot/src/counting.py#L94-L98)：
  ```python
  if buy_price == "-":
      real_time_price = get_field(record, "w")
  if sale_price == "-":
      up_low = "🎊"
      real_time_price = get_field(record, "u")
  ```
  [src/counting.py:108-110](file:///Users/davidtin/StockBot/src/counting.py#L108-L110)：
  ```python
  rise = ((real_time_price - yesterday_price) / yesterday_price) * 100
  # 跌時以 📉 取代 🎊，漲時附加 📈，持平時維持原樣
  up_low = rise_emoji(rise) if rise < 0 else up_low + rise_emoji(rise)
  ```
- 反例：
  若遇個股因重大訊息暫停交易（暫停撮合），或冷門股在非撮合時段無任何買賣盤掛單，TWSE API 回傳資料為買賣皆無委託：`b = "-"`（無買單）、`a = "-"`（無賣單）、`z = "-"`（無當盤成交價）、`y = "100.00"`（昨收）、`u = "110.00"`（漲停價）、`w = "90.00"`（跌停價）：
  1. 執行第 94 行：`buy_price == "-"` 為 True，`real_time_price` 暫設為 `w`（90.00）。
  2. 接著執行第 96 行：`sale_price == "-"` 亦為 True，`up_low` 被設為 `"🎊"`，且 `real_time_price` 被無條件覆蓋為漲停價 `u`（110.00）。
  3. 第 108 行計算漲跌幅：`rise = ((110.00 - 100.00) / 100.00) * 100 = 10.0`。
  4. 第 110 行判定 `rise > 0`，保留 `"🎊"` 並拼接為 `"🎊📈"`。
  5. 機器人對使用者輸出 `"2330 台積電 開盤：- \n當盤成交價 : 110.00 \t10.00% 🎊📈 "`。
  一檔因故暫停交易或市場無委託的股票，被誤報為飆漲 10% 漲停並慶祝，而非回傳 `PRICE_UNAVAILABLE_MESSAGE`。
- 建議修法：
  當 `buy_price == "-"` 且 `sale_price == "-"` 同時成立時，代表市場無雙邊委託（暫停交易或非交易時段無單），應回傳 `PRICE_UNAVAILABLE_MESSAGE`；僅在單邊為 `"-"` 時才處理漲停或跌停：
  ```python
  if buy_price == "-" and sale_price == "-":
      return PRICE_UNAVAILABLE_MESSAGE
  if buy_price == "-":
      real_time_price = get_field(record, "w")
  elif sale_price == "-":
      up_low = "🎊"
      real_time_price = get_field(record, "u")
  ```

[MAJOR] [src/counting.py:36](file:///Users/davidtin/StockBot/src/counting.py#L36) 與 [src/counting.py:42](file:///Users/davidtin/StockBot/src/counting.py#L42) — TWSE 回傳錯誤封包或缺少 `msgArray` 鍵時，直接存取屬性引發 `AttributeError` 崩潰
- 證據：
  [src/counting.py:36-43](file:///Users/davidtin/StockBot/src/counting.py#L36-L43)：
  ```python
  if len(stock_key.msgArray) <= 0:
      return STOCK_NOT_FOUND_MESSAGE

  res = requests.get(info_url_template.format(stock_key.msgArray[-1].key))
  info = json.loads(json.dumps(res.json()), object_hook=lambda d: SimpleNamespace(**d))

  if len(info.msgArray) <= 0:
      return STOCK_NOT_FOUND_MESSAGE
  ```
- 反例：
  當 TWSE 伺服器回傳業務錯誤回應（例如 session 過期、IP 頻率限制、或格式錯誤回傳 `{"rtcode": "9999", "rtmessage": "查無符合之資料"}`）時，JSON 字典內完全不包含 `"msgArray"` 鍵：
  1. `get_stock` 回傳包含 `rtcode` 的 `SimpleNamespace` 物件（非字串，第 34 行 `isinstance(stock_key, str)` 判定為 False）。
  2. 執行第 36 行 `len(stock_key.msgArray)`，因物件無該屬性直接拋出 `AttributeError: 'SimpleNamespace' object has no attribute 'msgArray'`。
  3. 實作雖抽取了 [src/counting.py:65](file:///Users/davidtin/StockBot/src/counting.py#L65) 的 `get_field` 防禦欄位缺漏，卻在最外層容器 `msgArray` 放棄防護，導致例外直接被 [src/pythonbot.py:47](file:///Users/davidtin/StockBot/src/pythonbot.py#L47) 捕捉，使用者收到的是 `FAILURE_MESSAGE`（「查詢失敗，請稍後再試」），而非宣稱的「查無代號時回傳明確錯誤提示」。第 42 行的 `info.msgArray` 亦存在完全相同的缺陷。
- 建議修法：
  在存取 `msgArray` 屬性前加入防禦：
  ```python
  stock_msg = getattr(stock_key, "msgArray", None)
  if not stock_msg:
      return STOCK_NOT_FOUND_MESSAGE
  ```
  以及：
  ```python
  info_msg = getattr(info, "msgArray", None)
  if not info_msg:
      return STOCK_NOT_FOUND_MESSAGE
  ```

[MINOR] [src/pythonbot.py:51](file:///Users/davidtin/StockBot/src/pythonbot.py#L51) — 指令失敗處理未檢查 `effective_message` 是否為 None，在無訊息之更新事件中引發二次例外
- 證據：
  [src/pythonbot.py:49-53](file:///Users/davidtin/StockBot/src/pythonbot.py#L49-L53)：
  ```python
  try:
      await update.effective_message.reply_text(FAILURE_MESSAGE)
  except Exception:
      logger.error('%s failure reply error', handler.__name__, exc_info=True)
  ```
- 反例：
  當更新事件中 `effective_message` 為 `None`（如 Telegram 之權限更新 `my_chat_member`、`inline_query` 或非訊息事件，如 [tests/test_price_flow.py:1075](file:///Users/davidtin/StockBot/tests/test_price_flow.py#L1075) 所示之 `update.effective_message = None`）：
  1. handler 發生例外進入外層 `except`。
  2. 第 51 行執行 `await update.effective_message.reply_text(FAILURE_MESSAGE)`，直接觸發 `AttributeError: 'NoneType' object has no attribute 'reply_text'`。
  3. 第 52 行捕獲後記錄 `logger.error('%s failure reply error', handler.__name__, exc_info=True)`，製造了無意義的二度崩潰日誌（掩蓋真實失敗原因）。
- 建議修法：
  發送失敗回覆前先判定物件是否存在：
  ```python
  msg = update.effective_message
  if msg:
      try:
          await msg.reply_text(FAILURE_MESSAGE)
      except Exception:
          logger.error('%s failure reply error', handler.__name__, exc_info=True)
  ```

[MINOR] [tests/test_pythonbot.py:1106](file:///Users/davidtin/StockBot/tests/test_pythonbot.py#L1106) — 測試套件保留未呼叫之死碼 helper，且既有測試斷言皆未真正綁定到 `effective_message`
- 證據：
  [tests/test_pythonbot.py:1106-1113](file:///Users/davidtin/StockBot/tests/test_pythonbot.py#L1106-L1113)：
  ```python
  def _edited_update(text="/price 2330"):
      """使用者編輯訊息：PTB 的 CommandHandler 仍會觸發，但 update.message 是 None。"""
      update = MagicMock()
      update.message = None
      update.effective_message.text = text
      update.effective_message.reply_text = AsyncMock()
      return update
  ```
  [tests/test_pythonbot.py:1098-1103](file:///Users/davidtin/StockBot/tests/test_pythonbot.py#L1098-L1103)：
  ```python
  def _update(text="/price 2330"):
      update = MagicMock()
      update.message.text = text
      update.message.reply_text = AsyncMock()
      update.effective_message = update.message
      return update
  ```
- 反例：
  `_edited_update` 函式在 [tests/test_pythonbot.py](file:///Users/davidtin/StockBot/tests/test_pythonbot.py) 中定義後，全檔 18 個測試中從未被任何測試呼叫過（呼叫次數為 0，純死碼）。
  且 [tests/test_pythonbot.py](file:///Users/davidtin/StockBot/tests/test_pythonbot.py) 內所有測試的斷言皆指向 `update.message.reply_text`（例如第 1147、1203、1234、1267、1284 行），若將 [src/pythonbot.py](file:///Users/davidtin/StockBot/src/pythonbot.py) 內的 `effective_message` 刻意改回造成崩潰的 `update.message`，[tests/test_pythonbot.py](file:///Users/davidtin/StockBot/tests/test_pythonbot.py) 依然會 100% 全部綠燈通過，完全未能在該模組測試內防守此行為（防守邏輯僅在另一檔案 [tests/test_price_flow.py](file:///Users/davidtin/StockBot/tests/test_price_flow.py) 被覆蓋）。
- 建議修法：
  在 [tests/test_pythonbot.py](file:///Users/davidtin/StockBot/tests/test_pythonbot.py) 中移除無用死碼，或將各指令之單元測試改以 `_edited_update` 驗證其行為，並將斷言統一指向 `update.effective_message.reply_text`。

---

## 疑慮

1. **內部審核記錄檔被簽入正式版控**：
   變更將 [docs/antigravity-review-price-nullsafe.md](file:///Users/davidtin/StockBot/docs/antigravity-review-price-nullsafe.md) 提交至版控中。該檔案為上階段 review 的審查過程產物（內含 conversation ID、審查標籤、EOF canary 等），不屬於專案功能程式碼或公開設計文件，污染了主要放 CSV 資料檔的 [docs/](file:///Users/davidtin/StockBot/docs/) 目錄。
2. **工作目錄（CWD）路徑假設依然脆弱**：
   [src/counting.py:7](file:///Users/davidtin/StockBot/src/counting.py#L7) 之 `PACKAGE_DIRECTORY = Path.cwd().parent.joinpath('docs')` 與 [src/fetchCode.py:59](file:///Users/davidtin/StockBot/src/fetchCode.py#L59) 之 `Path.cwd().parent.joinpath('docs')` 依然綁定「必須在 `src/` 底下執行」的假設。若從專案根目錄啟動且輸入中文名稱股票（例如 `/price 台積電`），`readCSV.read_csv` 會因找不到 CSV 檔案而引發 `FileNotFoundError`。
3. **跨模組邏輯缺乏單一來源**：
   - 漲跌幅 emoji 邏輯在 [src/counting.py:78](file:///Users/davidtin/StockBot/src/counting.py#L78) 與 [src/finnhub_client.py:58](file:///Users/davidtin/StockBot/src/finnhub_client.py#L58) 兩處各自維護。
   - `STOCK_NOT_FOUND_MESSAGE = "查無此代號，請確認輸入代號"` 雖抽取為常數，但 [src/finnhub_client.py:30](file:///Users/davidtin/StockBot/src/finnhub_client.py#L30) 與 [tests/test_price_flow.py:933](file:///Users/davidtin/StockBot/tests/test_price_flow.py#L933) 依然散落硬編碼字串。
4. **型態轉換過度依賴隱晦 fallback**：
   [src/counting.py:100](file:///Users/davidtin/StockBot/src/counting.py#L100) 的 `real_time_price = str(sale_price).split("_")[0]` 在 `sale_price` 為 `None` 時會產生 `"None"` 字串，隨後在第 102 行依賴 `to_float("None")` 捕捉 `ValueError` 回傳 `None`，流程隱晦脆弱。
5. **`/start` 錯誤訊息語意不合**：
   [src/pythonbot.py:59](file:///Users/davidtin/StockBot/src/pythonbot.py#L59) 的 `start` 套用 `@reply_on_failure`，若發送失敗會回覆「查詢失敗，請稍後再試」，然而 `/start` 並非查詢指令。
6. **設計文件未定義之規格**：
   [README.md](file:///Users/davidtin/StockBot/README.md) 未定義各指令在資料缺漏或非交易時段的回覆字串與行為，實作自行定義了回傳字串常數 `PRICE_UNAVAILABLE_MESSAGE` 與 `STOCK_NOT_FOUND_MESSAGE`。

---

## 無法驗證

1. **TWSE 外部 API 真實時段與異常回應結構**：
   無法在無網路與無指令執行環境下，實際連線 `https://mis.twse.com.tw` 驗證盤前試撮、盤中暫停交易、盤後清算等各真實時段回傳的欄位結構是否確實包含 `msgArray` 及相關報價欄位。
2. **Finnhub 外部限流行為**：
   無法透過真實外部請求驗證 Finnhub 60 calls/min rate limit 之行為。

---

CONTEXT_EOF: 9c33188ff7c77d54

## 結論
VERDICT: BLOCK
