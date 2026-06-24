# StockFetch

Telegram 股票報價機器人，支援台股與美股查詢。

## 指令

| 指令 | 說明 |
| --- | --- |
| `/price 股票代號` | 查詢台股即時股價，例如 `/price 2330` |
| `/odd_price 股票代號` | 查詢台股零股報價 |
| `/tse` | 查詢大盤指數 |
| `/usprice 美股代號` | 查詢美股即時股價（資料來源 finnhub.io），例如 `/usprice AAPL` |
| `/updateCsv` | 更新台股代號清單 |

## 環境變數

在 `src/env/.env` 設定以下變數：

```dotenv
TELEGRAM_ACCESS_TOKEN=<你的 Telegram bot token>
FINNHUB_API_KEY=<你的 finnhub.io API key>
INFO_LOG_PATH=/data/vault/logs/
ERROR_LOG_PATH=/data/vault/logs/
```

- `FINNHUB_API_KEY`：到 [finnhub.io](https://finnhub.io) 註冊免費取得；免費版 rate limit 約 60 calls/min，每次 `/usprice` 會呼叫 2 支 API（報價 + 公司名稱）。
- CI/CD 部署時請在 GitHub repo 的 Secrets 加入 `FINNHUB_API_KEY`。

## 執行

```bash
cd src && python pythonbot.py
```
