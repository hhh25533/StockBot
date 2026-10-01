# Antigravity 複驗：price-nullsafe
- date: 2026-10-01 08:14
- base: e054a08886bafd7b0fc618cfab4ac9a29c318aec
- head: c58b883fecd772ca6e55294be157614bdd65c6ff
- reviewer: antigravity-cli 1.2.14
- conversation: c1af8f74-dfaa-4d7a-9ebf-80b9676ad2e4

## 缺陷

[BLOCKER] [src/counting.py:34](file:///Users/davidtin/StockBot/src/counting.py#L33-L36) — `get_stock` 回傳錯誤訊息字串時，[`get_real_time_stock`](file:///Users/davidtin/StockBot/src/counting.py#L31-L45) 與 [`get_real_time_odd`](file:///Users/davidtin/StockBot/src/counting.py#L47-L61) 存取 `.msgArray` 引發 `AttributeError` 崩潰
- 證據：
  [src/counting.py:19](file:///Users/davidtin/StockBot/src/counting.py#L19)：
  ```python
  if stock == "" or stock is None: return "查無此代號，請確認輸入代號"
  ```
  [src/counting.py:33-35](file:///Users/davidtin/StockBot/src/counting.py#L33-L35)：
  ```python
  def get_real_time_stock(stock_id):

      stock_key = get_stock(stock_id)
      if len(stock_key.msgArray) <= 0:
          return "查無此代號，請確認輸入代號"
  ```
  [src/counting.py:49-51](file:///Users/davidtin/StockBot/src/counting.py#L49-L51)：
  ```python
  def get_real_time_odd(stock_id):

      stock_key = get_stock(stock_id)
      if len(stock_key.msgArray) <= 0:
          return "查無此代號，請確認輸入代號"
  ```
  [src/pythonbot.py:72-76](file:///Users/davidtin/StockBot/src/pythonbot.py#L72-L76)：
  ```python
  stock_info = counting.get_real_time_stock(stock_id)
  if isinstance(stock_info, str):
      await update.message.reply_text(stock_info)
      return
  ```
- 反例：
  使用者輸入非數字代號（例如 `/price TSMC`、`/price 假股票`、未帶參數的 `/price`、或 `/odd_price TSMC`）：
  1. [`get_stock`](file:///Users/davidtin/StockBot/src/counting.py#L14-L29) 判定 `not str(stock_id).isnumeric()` 為 `True`，至 CSV 比對名稱失敗，於 line 19 回傳 `str` 型別字串 `"查無此代號，請確認輸入代號"`。
  2. [`get_real_time_stock`](file:///Users/davidtin/StockBot/src/counting.py#L31-L45)（line 34）或 [`get_real_time_odd`](file:///Users/davidtin/StockBot/src/counting.py#L47-L61)（line 51）直接存取 `stock_key.msgArray`，因 `str` 沒有 `msgArray` 屬性，拋出 `AttributeError: 'str' object has no attribute 'msgArray'`。
  3. [src/pythonbot.py:73](file:///Users/davidtin/StockBot/src/pythonbot.py#L73) 的判斷 `isinstance(stock_info, str)` 根本無法執行到，例外直接被外層 [`reply_on_failure`](file:///Users/davidtin/StockBot/src/pythonbot.py#L39-L55) 捕獲，Telegram 使用者收到的是 `FAILURE_MESSAGE`（「查詢失敗，請稍後再試」），而非「查無此代號，請確認輸入代號」。宣稱的「查無代號時不再靜默失敗」在非數字代號上完全失靈。
- 建議修法：
  在 [`get_real_time_stock`](file:///Users/davidtin/StockBot/src/counting.py#L31-L45) 與 [`get_real_time_odd`](file:///Users/davidtin/StockBot/src/counting.py#L47-L61) 內，存取 `.msgArray` 前先檢查 `stock_key` 是否為字串或物件是否具備該屬性：
  ```python
  if isinstance(stock_key, str):
      return stock_key
  if not hasattr(stock_key, "msgArray") or len(stock_key.msgArray) <= 0:
      return "查無此代號，請確認輸入代號"
  ```

[MAJOR] [src/counting.py:138](file:///Users/davidtin/StockBot/src/counting.py#L138) — 當盤成交價為 0.00 時未判定為無效，計算出 -100.00% 暴跌輸出
- 證據：
  [src/counting.py:136-142](file:///Users/davidtin/StockBot/src/counting.py#L136-L142)：
  ```python
  real_time_price = to_float(real_time_price)
  yesterday_price = to_float(get_field(record, "y"))
  if real_time_price is None or not yesterday_price:
      return PRICE_UNAVAILABLE_MESSAGE

  open_price = to_float(get_field(record, "o"))
  rise = ((real_time_price - yesterday_price) / yesterday_price) * 100
  ```
  [src/counting.py:164-169](file:///Users/davidtin/StockBot/src/counting.py#L164-L169)：
  ```python
  real_time = to_float(get_field(record, "z"))
  yesterday_price = to_float(get_field(record, "y"))
  if real_time is None or not yesterday_price:
      return PRICE_UNAVAILABLE_MESSAGE

  rise = ((real_time - yesterday_price) / yesterday_price) * 100
  ```
- 反例：
  交易所資料在非交易時段重置或開盤未撮合時，TWSE 回傳之 `z` 欄位可能為 `"0.00"` 或 `0`。傳入 `_stock(z="0.00", y="100.00", c="2330", n="台積電")`：
  1. [`to_float("0.00")`](file:///Users/davidtin/StockBot/src/counting.py#L93-L99) 回傳 `0.0`。
  2. `if real_time_price is None or not yesterday_price:` 中，`0.0 is None` 為 `False`，檢查放行。
  3. 執行 line 142：`rise = ((0.0 - 100.00) / 100.00) * 100`，計算出 `rise = -100.0`。
  4. 輸出 `"2330 台積電 開盤：- \n當盤成交價 : 0.00 \t-100.00% 📉 "`。
  台股個股與大盤指數皆不可能成交於 0 元，顯示 -100.00% 顯然為資料未撮合的無效狀態，應當回傳 `PRICE_UNAVAILABLE_MESSAGE`。
- 建議修法：
  在 [src/counting.py:138](file:///Users/davidtin/StockBot/src/counting.py#L138) 與 [src/counting.py:166](file:///Users/davidtin/StockBot/src/counting.py#L166) 將條件修正為對 0 值防護：
  ```python
  if not real_time_price or not yesterday_price:
      return PRICE_UNAVAILABLE_MESSAGE
  ```

[MAJOR] [src/pythonbot.py:50](file:///Users/davidtin/StockBot/src/pythonbot.py#L50) — 指令失敗處理使用 `update.message.reply_text`，在編輯訊息或 `message` 為 None 時引發二次例外導致靜默失聯
- 證據：
  [src/pythonbot.py:44-53](file:///Users/davidtin/StockBot/src/pythonbot.py#L44-L53)：
  ```python
  try:
      await handler(update, context)
  except Exception as e:
      logger.error('%s error', handler.__name__)
      logger.error(e, exc_info=True)
      try:
          await update.message.reply_text(FAILURE_MESSAGE)
      except Exception:
          logger.error('%s failure reply error', handler.__name__, exc_info=True)
  ```
  [src/pythonbot.py:71](file:///Users/davidtin/StockBot/src/pythonbot.py#L71)：
  ```python
  stock_id = update.message.text[7:].replace('\n', ' ')
  ```
- 反例：
  使用者在 Telegram 聊天室編輯已送出的訊息（例如先前輸入錯誤，透過編輯修改指令內容）：
  1. Telegram 更新封包中，`update.message` 為 `None`，訊息存放於 `update.edited_message`。
  2. [`quoted`](file:///Users/davidtin/StockBot/src/pythonbot.py#L67-L78) 執行 line 71 的 `update.message.text`，拋出 `AttributeError: 'NoneType' object has no attribute 'text'`。
  3. 外層 `except` 捕捉後，執行 line 50 的 `await update.message.reply_text(FAILURE_MESSAGE)`。
  4. 由於 `update.message` 為 `None`，再次拋出 `AttributeError: 'NoneType' object has no attribute 'reply_text'`。
  5. 內層 `except` 吞掉該錯誤，使用者端完全未收到任何訊息反饋，違反了 `FAILURE_MESSAGE`「使用者不該遇到『完全沒反應』」的設計初衷。
- 建議修法：
  改用 `update.effective_message` 並做空值防禦：
  ```python
  msg = update.effective_message
  if msg:
      await msg.reply_text(FAILURE_MESSAGE)
  ```

[MAJOR] [tests/test_pythonbot.py:34](file:///Users/davidtin/StockBot/tests/test_pythonbot.py#L34) — 測試以 fake mock 掩蓋真實 counting 模組的 AttributeError 崩潰
- 證據：
  [tests/test_pythonbot.py:33-43](file:///Users/davidtin/StockBot/tests/test_pythonbot.py#L33-L43)：
  ```python
  async def test_quoted_string_result_replies_once_and_skips_generate_response(monkeypatch):
      monkeypatch.setattr(counting, "get_real_time_stock", lambda _id: "查無此代號，請確認輸入代號")
      generate = MagicMock()
      monkeypatch.setattr(counting, "generate_response", generate)
      update = _update()

      await pythonbot.quoted(update, MagicMock())

      update.message.reply_text.assert_awaited_once_with("查無此代號，請確認輸入代號")
      generate.assert_not_called()
  ```
  [tests/test_pythonbot.py:99-109](file:///Users/davidtin/StockBot/tests/test_pythonbot.py#L99-L109)：
  ```python
  async def test_odd_quoted_string_result_replies_once_and_skips_generate_response(monkeypatch):
      monkeypatch.setattr(counting, "get_real_time_odd", lambda _id: "查無此代號，請確認輸入代號")
      generate = MagicMock()
      monkeypatch.setattr(counting, "generate_response", generate)
      update = _update("/odd_price 2330")

      await pythonbot.odd_quoted(update, MagicMock())

      update.message.reply_text.assert_awaited_once_with("查無此代號，請確認輸入代號")
      generate.assert_not_called()
  ```
- 反例：
  本 PR 的 commit 訊息宣稱「fix: /price、/odd_price 在欄位缺漏與查無代號時不再靜默失敗」。
  若在測試中移除 monkeypatch 並給入真實非數字代號（例如 `"UNKNOWN"`）：
  `counting.get_real_time_stock("UNKNOWN")` 必然在 [src/counting.py:34](file:///Users/davidtin/StockBot/src/counting.py#L34) 拋出 `AttributeError: 'str' object has no attribute 'msgArray'`，根本不可能回傳字串。
  測試刻意將受測對象 mock 成保證回傳字串的 fake，製造出修正通過的假象，掩蓋了模組接縫處的致命錯誤；且 [tests/test_counting.py](file:///Users/davidtin/StockBot/tests/test_counting.py) 完全未對 [`get_stock`](file:///Users/davidtin/StockBot/src/counting.py#L14-L29)、[`get_real_time_stock`](file:///Users/davidtin/StockBot/src/counting.py#L31-L45) 進行任何測試。
- 建議修法：
  修正 [src/counting.py:34](file:///Users/davidtin/StockBot/src/counting.py#L34) 的型態合約問題，並在測試套件中對真實函數呼叫或更底層的網路/CSV 依賴進行 mock，驗證真實函式交界處的行為。

[MINOR] [src/counting.py:163](file:///Users/davidtin/StockBot/src/counting.py#L163) — [`generate_tse_response`](file:///Users/davidtin/StockBot/src/counting.py#L162-L176) 在 `tse_info` 為空清單時直接報 `IndexError`
- 證據：
  [src/counting.py:162-164](file:///Users/davidtin/StockBot/src/counting.py#L162-L164)：
  ```python
  def generate_tse_response(tse_info):
      record = tse_info[-1]
  ```
  [src/pythonbot.py:96-97](file:///Users/davidtin/StockBot/src/pythonbot.py#L96-L97)：
  ```python
  @reply_on_failure
  async def tse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
      tse_info = counting.get_real_time_tse()
      await update.message.reply_text(counting.generate_tse_response(tse_info))
  ```
- 反例：
  TWSE 維護期間或 API 回應異常，導致 [`counting.get_real_time_tse()`](file:///Users/davidtin/StockBot/src/counting.py#L63-L70) 回傳空清單 `[]`：
  1. 呼叫 `generate_tse_response([])`。
  2. line 163 `record = tse_info[-1]` 拋出 `IndexError: list index out of range`。
  3. 未能如預期回傳 `PRICE_UNAVAILABLE_MESSAGE`，而是由外層捕獲為未預期錯誤，回覆「查詢失敗，請稍後再試」。
- 建議修法：
  在 [src/counting.py:163](file:///Users/davidtin/StockBot/src/counting.py#L163) 開頭檢查空清單：
  ```python
  if not tse_info:
      return PRICE_UNAVAILABLE_MESSAGE
  ```

[MINOR] [src/pythonbot.py:92](file:///Users/davidtin/StockBot/src/pythonbot.py#L92) — [`odd_quoted`](file:///Users/davidtin/StockBot/src/pythonbot.py#L81-L93) 對錯誤訊息無條件拼接 "零股\n" 前綴
- 證據：
  [src/pythonbot.py:91-92](file:///Users/davidtin/StockBot/src/pythonbot.py#L91-L92)：
  ```python
  await update.message.reply_text("零股\n" + counting.generate_response(odd_info))
  ```
- 反例：
  非交易時段查詢零股時，[`counting.generate_response(odd_info)`](file:///Users/davidtin/StockBot/src/counting.py#L109-L160) 回傳 `PRICE_UNAVAILABLE_MESSAGE`（「目前無法取得成交價（可能為非交易時段），請於交易時間再查詢」）：
  [`odd_quoted`](file:///Users/davidtin/StockBot/src/pythonbot.py#L81-L93) 未做任何條件分支，直接拼接字串，使用者收到：
  `"零股\n目前無法取得成交價（可能為非交易時段），請於交易時間再查詢"`
  前綴「零股\n」出現在錯誤提示前，格式不合邏輯。
- 建議修法：
  ```python
  resp = counting.generate_response(odd_info)
  if resp == counting.PRICE_UNAVAILABLE_MESSAGE:
      await update.message.reply_text(resp)
  else:
      await update.message.reply_text("零股\n" + resp)
  ```

[MINOR] [src/pythonbot.py:71](file:///Users/davidtin/StockBot/src/pythonbot.py#L71) 與 [src/pythonbot.py:85](file:///Users/davidtin/StockBot/src/pythonbot.py#L85) — 參數切割未做 strip，指令含多餘空格會被誤判為股票名稱而引發崩潰
- 證據：
  [src/pythonbot.py:71](file:///Users/davidtin/StockBot/src/pythonbot.py#L71)：
  ```python
  stock_id = update.message.text[7:].replace('\n', ' ')
  ```
  [src/pythonbot.py:85](file:///Users/davidtin/StockBot/src/pythonbot.py#L85)：
  ```python
  stock_id = update.message.text[11:].replace('\n', ' ')
  ```
- 反例：
  使用者輸入 `/price  2330`（`/price` 與代號間有多餘空格）或 `/price 2330 `：
  1. `update.message.text[7:]` 切出的 `stock_id` 為 `" 2330"`。
  2. [`counting.get_stock(" 2330")`](file:///Users/davidtin/StockBot/src/counting.py#L14-L29) 執行 `not str(" 2330").isnumeric()`，因前導空格判定為非數字，進入名稱比對。
  3. CSV 比對失敗回傳字串，觸發上述 Defect 1 的 `AttributeError` 崩潰，使用者收到「查詢失敗，請稍後再試」。
- 建議修法：
  改用 `context.args` 或在字串切割後加上 `.strip()`：
  ```python
  stock_id = update.message.text[7:].strip().replace('\n', ' ')
  ```

---

## 疑慮

1. **路徑對當前工作目錄（CWD）有強烈隱性假設**：
   [src/counting.py:7](file:///Users/davidtin/StockBot/src/counting.py#L7) 定義 `PACKAGE_DIRECTORY = Path.cwd().parent.joinpath('docs')`，[src/pythonbot.py:120](file:///Users/davidtin/StockBot/src/pythonbot.py#L120) 定義 `load_dotenv("env/.env")`。這依賴於使用者嚴格在 `src/` 目錄下啟動。若從專案根目錄執行 `python src/pythonbot.py` 或執行未 mock 該路徑的整合測試，`Path.cwd().parent` 會指向專案目錄外層，導致 `docs/twse_equities.csv` 與 `env/.env` 發生 `FileNotFoundError`。
2. **同步阻塞 I/O 位於非同步事件迴圈中**：
   [src/pythonbot.py:112-114](file:///Users/davidtin/StockBot/src/pythonbot.py#L112-L114) 的 [`update_csv`](file:///Users/davidtin/StockBot/src/pythonbot.py#L112-L115) 呼叫 [`fetchCode.update_codes()`](file:///Users/davidtin/StockBot/src/fetchCode.py#L57-L62)。該函數同步發起 HTTP requests 下載數萬筆資料並解析 XML、寫入磁碟，未透過 `asyncio.to_thread` 移至背景執行緒執行，執行期間會卡死整支 Bot 的 asyncio event loop，造成其他指令全部無響應。
3. **跨模組重構缺乏單一來源**：
   - 漲跌幅 emoji 的判定邏輯在 [src/counting.py:101-106](file:///Users/davidtin/StockBot/src/counting.py#L101-L106)（[`rise_emoji`](file:///Users/davidtin/StockBot/src/counting.py#L101-L106)）與 [src/finnhub_client.py:58-61](file:///Users/davidtin/StockBot/src/finnhub_client.py#L58-L61) 兩處重複實作，未抽取為公用函式。
   - 錯誤訊息 `"查無此代號，請確認輸入代號"` 分散於 [src/counting.py](file:///Users/davidtin/StockBot/src/counting.py#L19)、[src/finnhub_client.py](file:///Users/davidtin/StockBot/src/finnhub_client.py#L30) 與測試中多處，未如 `PRICE_UNAVAILABLE_MESSAGE` 一樣抽取為常數。
4. **設計文件未定義之規格**：
   [README.md](file:///Users/davidtin/StockBot/README.md) 未定義各指令在非交易時段或資料缺漏時應回覆的文字格式與行為，實作自行決定了回傳字串常數 `PRICE_UNAVAILABLE_MESSAGE`。
5. **大盤指數共用個股錯誤常數之文字不匹配**：
   [src/counting.py:167](file:///Users/davidtin/StockBot/src/counting.py#L167) [`generate_tse_response`](file:///Users/davidtin/StockBot/src/counting.py#L162-L176) 回傳 `PRICE_UNAVAILABLE_MESSAGE`，導致大盤指數缺漏時回覆使用者「目前無法取得**成交價**（可能為非交易時段）」，用詞為個股的「成交價」而非大盤點數。

---

## 無法驗證

1. **TWSE 外部 API 真實回應格式與時段行為**：
   因沙盒環境禁止任意網路連線與命令執行，且當前非台股實際開盤時段，無法真實連線 `https://mis.twse.com.tw` 驗證 TWSE 於盤前試撮、盤中、盤後與假日維護時回傳的即時欄位是否確實符合 `get_field` 的所有防護假設。
2. **Finnhub API 外部限流與權限驗證**：
   無法透過真實 API 呼叫驗證 Finnhub 之 60 calls/min rate limit 與 Profile 查詢失敗時的網路退避邏輯。

---

CONTEXT_EOF: 2dc7ade672c5452c

## 結論
VERDICT: BLOCK
