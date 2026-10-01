import functools
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import fetchCode
import counting
import finnhub_client
from dotenv import load_dotenv
import logging

DEFAULT_LOG_DIR = "/data/vault/logs/"

# 處理指令失敗時回給使用者的訊息；使用者不該遇到「完全沒反應」。
FAILURE_MESSAGE = "查詢失敗，請稍後再試"
START_FAILURE_MESSAGE = "目前無法顯示使用說明，請稍後再試"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def setup_logging() -> None:
    """建立寫檔的 log handler。只在啟動時呼叫，避免 import 時就去碰 /data/vault/logs/。"""
    formater = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    info_log_path = os.getenv('INFO_LOG_PATH') or DEFAULT_LOG_DIR
    error_log_path = os.getenv('ERROR_LOG_PATH') or DEFAULT_LOG_DIR

    info_handler = logging.FileHandler(info_log_path + 'info.log')
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formater)

    error_handler = logging.FileHandler(error_log_path + 'error.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formater)

    logger.addHandler(error_handler)
    logger.addHandler(info_handler)


def reply_on_failure(failure_message=FAILURE_MESSAGE):
    """指令處理失敗時：記 log，並回覆使用者一句失敗訊息（回覆本身失敗也不再往外拋）。"""

    def decorator(handler):
        @functools.wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            try:
                await handler(update, context)
            except Exception as e:
                logger.error('%s error', handler.__name__)
                logger.error(e, exc_info=True)
                message = update.effective_message
                if message is None:
                    logger.error('%s 沒有可回覆的訊息（effective_message 為 None），略過失敗回覆', handler.__name__)
                    return
                try:
                    await message.reply_text(failure_message)
                except Exception:
                    logger.error('%s failure reply error', handler.__name__, exc_info=True)

        return wrapper

    return decorator


# 傳送訊息給使用者
@reply_on_failure(START_FAILURE_MESSAGE)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="歡迎使用股票報價系統 \n 基本使用方法:\n 1. /price 股票代號 (查詢股價)\n 2./odd_price 股票代號 (零股報價)\n 3. /tse 大盤指數\n 4. /usprice 美股代號 (查詢美股股價)"
    )


@reply_on_failure()
async def quoted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 限制只有特定人才能新增語錄
    # if update.message.from_user.id == YOUR_USER_ID_HERE:
    if True:
        stock_id = update.effective_message.text[7:].replace('\n', ' ').strip()
        stock_info = counting.get_real_time_stock(stock_id)
        if isinstance(stock_info, str):
            await update.effective_message.reply_text(stock_info)
            return

        await update.effective_message.reply_text(counting.generate_response(stock_info))


@reply_on_failure()
async def odd_quoted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 限制只有特定人才能新增語錄
    # if update.message.from_user.id == YOUR_USER_ID_HERE:
    if True:
        stock_id = update.effective_message.text[11:].replace('\n', ' ').strip()
        odd_info = counting.get_real_time_odd(stock_id)
        if isinstance(odd_info, str):
            await update.effective_message.reply_text(odd_info)
            return

        response = counting.generate_response(odd_info)
        if response != counting.PRICE_UNAVAILABLE_MESSAGE:
            response = "零股\n" + response
        await update.effective_message.reply_text(response)


@reply_on_failure()
async def tse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tse_info = counting.get_real_time_tse()
    await update.effective_message.reply_text(counting.generate_tse_response(tse_info))


@reply_on_failure()
async def us_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    symbol = " ".join(context.args)
    us_info = finnhub_client.get_us_stock_quote(symbol)
    if isinstance(us_info, str):
        await update.effective_message.reply_text(us_info)
        return

    await update.effective_message.reply_text(finnhub_client.generate_us_response(us_info))


@reply_on_failure()
async def update_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    fetchCode.update_codes()
    await update.effective_message.reply_text("更新完成")


def main() -> None:
    # 僅供本機開發使用：檔案不存在時 load_dotenv 不會拋錯、也不影響流程，
    # 正式環境的變數一律由 docker-compose 的 environment 區塊在執行期注入。
    load_dotenv("env/.env")

    setup_logging()

    logger.info("Bot is running")

    # fail-closed：缺少 TELEGRAM_ACCESS_TOKEN 就直接終止，不讓 None 傳進 telegram 套件
    # 內部（那裡拋出的是不易理解的 InvalidToken）。
    telegram_access_token = os.getenv('TELEGRAM_ACCESS_TOKEN')
    if not telegram_access_token:
        raise RuntimeError(
            "缺少必要環境變數 TELEGRAM_ACCESS_TOKEN，請在 docker-compose 或執行環境中設定後再啟動。"
        )

    # FINNHUB_API_KEY 只影響 /usprice 這個指令（finnhub_client.get_us_stock_quote 會在缺
    # key 時回覆使用者明確錯誤訊息），不影響整支 bot 的其他指令，因此這裡只記警告，不終止啟動。
    if not os.getenv('FINNHUB_API_KEY'):
        logger.warning("未設定 FINNHUB_API_KEY，/usprice 指令將無法查詢美股報價。")

    app = ApplicationBuilder().token(telegram_access_token).build()

    app.add_handler(CommandHandler("start", start))  # 把此 Handler 加入派送任務中
    app.add_handler(CommandHandler("price", quoted))
    app.add_handler(CommandHandler("odd_price", odd_quoted))
    app.add_handler(CommandHandler("tse", tse))
    app.add_handler(CommandHandler("usprice", us_price))
    app.add_handler(CommandHandler("updateCsv", update_csv))

    app.run_polling()  # 開始推送任務

    # updater.stop()  # 停止推送任務


if __name__ == "__main__":
    main()
