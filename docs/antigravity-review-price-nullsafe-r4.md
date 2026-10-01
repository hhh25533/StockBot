# Antigravity 複驗：price-nullsafe-r4
- date: 2026-10-01 08:38
- base: e054a08886bafd7b0fc618cfab4ac9a29c318aec
- head: e8a7a3d2ee572f92c94e11597574b53770d5af78
- reviewer: antigravity-cli 1.2.14
- conversation: 42b23770-3f3e-419f-a147-6118b935caaa

## 缺陷

無

## 疑慮

1. **內部審核記錄檔被簽入正式版控**：
   變更將 [docs/antigravity-review-price-nullsafe.md](file:///Users/davidtin/StockBot/docs/antigravity-review-price-nullsafe.md)、[docs/antigravity-review-price-nullsafe-r2.md](file:///Users/davidtin/StockBot/docs/antigravity-review-price-nullsafe-r2.md) 與 [docs/antigravity-review-price-nullsafe-r3.md](file:///Users/davidtin/StockBot/docs/antigravity-review-price-nullsafe-r3.md) 提交至版控中。該三份檔案為歷史審查產物（內含 conversation ID、審查標籤、EOF canary 等），不屬於專案功能程式碼或公開設計文件，污染了主要存放 CSV 資料檔的 [docs/](file:///Users/davidtin/StockBot/docs/) 目錄。
2. **工作目錄（CWD）路徑假設依然脆弱**：
   [src/counting.py:7](file:///Users/davidtin/StockBot/src/counting.py#L7) 之 `PACKAGE_DIRECTORY = Path.cwd().parent.joinpath('docs')` 與 [src/fetchCode.py:59](file:///Users/davidtin/StockBot/src/fetchCode.py#L59) 之 `Path.cwd().parent.joinpath('docs')` 依然綁定「必須在 `src/` 底下執行」的假設。若從專案根目錄啟動（例如 `python src/pythonbot.py`）且輸入中文名稱股票（例如 `/price 台積電`），`readCSV.read_csv` 會因找不到 CSV 檔案而引發 `FileNotFoundError`。
3. **跨模組邏輯與常數缺乏單一來源**：
   - 漲跌幅 emoji 邏輯在 [src/counting.py:81-86](file:///Users/davidtin/StockBot/src/counting.py#L81-L86) 與 [src/finnhub_client.py:56-62](file:///Users/davidtin/StockBot/src/finnhub_client.py#L56-L62) 兩處各自維護。
   - `STOCK_NOT_FOUND_MESSAGE = "查無此代號，請確認輸入代號"` 雖抽取為常數，但 [src/finnhub_client.py:30](file:///Users/davidtin/StockBot/src/finnhub_client.py#L30) 與 [tests/test_price_flow.py:14](file:///Users/davidtin/StockBot/tests/test_price_flow.py#L14) 依然散落硬編碼字串。
4. **非同步 Handler 內存在同步阻塞 I/O**：
   [src/pythonbot.py:124](file:///Users/davidtin/StockBot/src/pythonbot.py#L124) 的 `update_csv` 呼叫 [src/fetchCode.py:57-62](file:///Users/davidtin/StockBot/src/fetchCode.py#L57-L62) 之 `fetchCode.update_codes()`，在 asyncio 事件迴圈中同步發出 HTTP 請求下載並解析大量資料，期間會卡死機器人事件迴圈。
5. **`/updateCsv` 失敗回覆訊息語意不匹配**：
   [src/pythonbot.py:122](file:///Users/davidtin/StockBot/src/pythonbot.py#L122) 之 `update_csv` 使用預設的 `@reply_on_failure()`，若更新失敗會回覆使用者「查詢失敗，請稍後再試」，然而 `/updateCsv` 並非查詢指令。
6. **大盤指數共用個股錯誤常數之文字不匹配**：
   [src/counting.py:130](file:///Users/davidtin/StockBot/src/counting.py#L130) 與 [src/counting.py:135](file:///Users/davidtin/StockBot/src/counting.py#L135) 之 `generate_tse_response` 回傳 `PRICE_UNAVAILABLE_MESSAGE`，導致大盤指數缺漏時回覆使用者「目前無法取得**成交價**（可能為非交易時段）」，用詞為個股的「成交價」而非大盤點數。
7. **設計文件未定義之規格**：
   [README.md](file:///Users/davidtin/StockBot/README.md) 未定義各指令在資料缺漏或非交易時段的回覆字串與行為，實作自行定義了回傳字串常數 `PRICE_UNAVAILABLE_MESSAGE`、`STOCK_NOT_FOUND_MESSAGE`、`FAILURE_MESSAGE` 與 `START_FAILURE_MESSAGE`。

## 無法驗證

1. **TWSE 外部 API 真實時段與異常回應結構**：
   在無網路連線與命令執行權限下，無法真實連線 `https://mis.twse.com.tw` 驗證盤前試撮、盤中暫停交易、盤後清算等各真實時段回傳的欄位結構是否確實包含 `msgArray` 及相關報價欄位。
2. **Finnhub 外部限流與權限行為**：
   無法透過真實外部請求驗證 Finnhub 60 calls/min rate limit 之行為。

CONTEXT_EOF: 31b5b8e76424990b

## 結論
VERDICT: PASS
