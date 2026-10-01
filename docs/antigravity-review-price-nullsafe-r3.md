# Antigravity 複驗：price-nullsafe-r3
- date: 2026-10-01 08:28
- base: e054a08886bafd7b0fc618cfab4ac9a29c318aec
- head: 1d390d679ef8be84f59db82db4a1e54a09b28ff3
- reviewer: antigravity-cli 1.2.14
- conversation: 315ca15c-040b-4233-a8fa-14a1fe6ac5cd

## 缺陷

[MINOR] [tests/test_pythonbot.py:12-17](file:///Users/davidtin/StockBot/tests/test_pythonbot.py#L12-L17) — 模組單元測試斷言皆綁定至 `update.message.reply_text`，且多數指令缺乏編輯訊息測試，未能防守 `effective_message` 行為
- 證據：
  [tests/test_pythonbot.py:12-17](file:///Users/davidtin/StockBot/tests/test_pythonbot.py#L12-L17)：
  ```python
  def _update(text="/price 2330"):
      update = MagicMock()
      update.message.text = text
      update.message.reply_text = AsyncMock()
      update.effective_message = update.message
      return update
  ```
  在 [tests/test_pythonbot.py](file:///Users/davidtin/StockBot/tests/test_pythonbot.py) 中，所有的回覆斷言皆指向 `update.message.reply_text`（例如第 42、52、64、85、95、108、119、128、140、149、158、172、184、192、195、204 行）：
  ```python
  update.message.reply_text.assert_awaited_once()
  ```
- 反例：
  1. 使用者在 Telegram 編輯已送出之訊息以觸發 `/tse`（或 `/usprice AAPL`、`/updateCsv`、`/start`）。此時 Telegram 更新事件中 `update.message` 為 `None`，訊息本體存放於 `update.effective_message`。
  2. 若維護者刻意將 [src/pythonbot.py:108](file:///Users/davidtin/StockBot/src/pythonbot.py#L108) 的 `await update.effective_message.reply_text(...)` 改回造成崩潰的 `await update.message.reply_text(...)`：
     - [tests/test_price_flow.py](file:///Users/davidtin/StockBot/tests/test_price_flow.py) 僅對 `quoted` 與 `odd_quoted` 撰寫了 `edited=True` 的測試（第 137、143 行），完全沒有覆蓋 `tse`、`us_price`、`update_csv` 與 `start`。
     - [tests/test_pythonbot.py](file:///Users/davidtin/StockBot/tests/test_pythonbot.py) 內 `_update()` 將 `update.effective_message` 與 `update.message` 指向同一 mock 物件，且斷言全部檢驗 `update.message.reply_text`。
  3. 執行整個測試套件，結果依然 100% 全部通過綠燈，無任何測試變紅，測試套件未能對這些指令防守宣稱的「編輯訊息不漏接」之契約。
- 建議修法：
  在 [tests/test_pythonbot.py](file:///Users/davidtin/StockBot/tests/test_pythonbot.py) 中將所有斷言改為 `update.effective_message.reply_text.assert_awaited_once()`，並在 `_update` 中讓 `update.message` 與 `update.effective_message` 分離（或在部分單元測試中設 `update.message = None`），同時於 [tests/test_price_flow.py](file:///Users/davidtin/StockBot/tests/test_price_flow.py) 補上 `tse`、`us_price` 與 `update_csv` 的編輯訊息測試。

---

## 疑慮

1. **內部審核記錄檔被簽入正式版控**：
   變更將 [docs/antigravity-review-price-nullsafe.md](file:///Users/davidtin/StockBot/docs/antigravity-review-price-nullsafe.md) 與 [docs/antigravity-review-price-nullsafe-r2.md](file:///Users/davidtin/StockBot/docs/antigravity-review-price-nullsafe-r2.md) 提交至版控中。該二檔案為歷史審查產物（內含 conversation ID、審查標籤、EOF canary 等），不屬於專案程式碼或公開設計文件，污染了主要存放 CSV 資料檔的 [docs/](file:///Users/davidtin/StockBot/docs/) 目錄。
2. **工作目錄（CWD）路徑假設依然脆弱**：
   [src/counting.py:7](file:///Users/davidtin/StockBot/src/counting.py#L7) 之 `PACKAGE_DIRECTORY = Path.cwd().parent.joinpath('docs')` 與 [src/fetchCode.py:59](file:///Users/davidtin/StockBot/src/fetchCode.py#L59) 之 `Path.cwd().parent.joinpath('docs')` 依然綁定「必須在 `src/` 底下執行」的假設。若從專案根目錄啟動且輸入中文名稱股票（例如 `/price 台積電`），`readCSV.read_csv` 會因找不到 CSV 檔案而引發 `FileNotFoundError`。
3. **跨模組邏輯與常數缺乏單一來源**：
   - 漲跌幅 emoji 邏輯在 [src/counting.py:81-86](file:///Users/davidtin/StockBot/src/counting.py#L81-L86) 與 [src/finnhub_client.py:56-62](file:///Users/davidtin/StockBot/src/finnhub_client.py#L56-L62) 兩處各自維護。
   - `STOCK_NOT_FOUND_MESSAGE = "查無此代號，請確認輸入代號"` 雖抽取為常數，但 [src/finnhub_client.py:30](file:///Users/davidtin/StockBot/src/finnhub_client.py#L30) 與 [tests/test_price_flow.py:14](file:///Users/davidtin/StockBot/tests/test_price_flow.py#L14) 依然散落硬編碼字串。
4. **非同步 Handler 內存在同步阻塞 I/O**：
   [src/pythonbot.py:123-125](file:///Users/davidtin/StockBot/src/pythonbot.py#L123-L125) 的 `update_csv` 呼叫 [src/fetchCode.py:57-62](file:///Users/davidtin/StockBot/src/fetchCode.py#L57-L62) 之 `fetchCode.update_codes()`，在 asyncio 事件迴圈中同步發出 HTTP 請求下載並解析大量資料，期間會卡死機器人事件迴圈。
5. **`/updateCsv` 失敗回覆訊息語意不匹配**：
   [src/pythonbot.py:123](file:///Users/davidtin/StockBot/src/pythonbot.py#L123) 之 `update_csv` 使用預設的 `@reply_on_failure()`，若更新失敗會回覆使用者「查詢失敗，請稍後再試」，然而 `/updateCsv` 並非查詢指令。
6. **設計文件未定義之規格**：
   [README.md](file:///Users/davidtin/StockBot/README.md) 未定義各指令在資料缺漏或非交易時段的回覆字串與行為，實作自行定義了回傳字串常數 `PRICE_UNAVAILABLE_MESSAGE` 與 `STOCK_NOT_FOUND_MESSAGE`。

---

## 無法驗證

1. **TWSE 外部 API 真實時段與異常回應結構**：
   在無網路連線與命令執行權限下，無法真實連線 `https://mis.twse.com.tw` 驗證盤前試撮、盤中暫停交易、盤後清算等各真實時段回傳的欄位結構是否確實包含 `msgArray` 及相關報價欄位。
2. **Finnhub 外部限流與權限行為**：
   無法透過真實外部請求驗證 Finnhub 60 calls/min rate limit 之行為。

---

CONTEXT_EOF: 4dd3470cd1b88348

## 結論
VERDICT: PASS
