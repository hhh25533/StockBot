import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import fetchCode
import counting
from dotenv import load_dotenv

load_dotenv("env/.env")


print(os.getenv('TELEGRAM_ACCESS_TOKEN'))


app = ApplicationBuilder().token(os.getenv('TELEGRAM_ACCESS_TOKEN')).build()


# 傳送訊息給使用者
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="歡迎使用股票報價系統 \n 基本使用方法:\n 1. /price 股票代號 (查詢股價)\n 2. /tse 大盤指數"
    )


async def quoted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 限制只有特定人才能新增語錄
    # if update.message.from_user.id == YOUR_USER_ID_HERE:
    if True:
        stock_id = update.message.text[7:].replace('\n', ' ')
        stock_info = counting.get_real_time_stock(stock_id)
        if isinstance(stock_info, str):
            await update.message.reply_text(stock_info)

        await update.message.reply_text(counting.generate_response(stock_info))


async def odd_quoted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 限制只有特定人才能新增語錄
    # if update.message.from_user.id == YOUR_USER_ID_HERE:
    if True:
        stock_id = update.message.text[11:].replace('\n', ' ')
        odd_info = counting.get_real_time_odd(stock_id)
        if isinstance(odd_info, str):
            await update.message.reply_text(odd_info)

        await update.message.reply_text("零股\n"+counting.generate_response(odd_info))


async def tse(update: Update,  context: ContextTypes.DEFAULT_TYPE) -> None:
    tse_info = counting.get_real_time_tse()

    real_time = tse_info[-1].z
    yesterday_price = tse_info[-1].y

    rise = ((float(real_time) - float(yesterday_price)) / float(yesterday_price)) * 100

    up_low = ""
    if rise < 0:
        up_low = "📉"
    if rise > 0:
        up_low = "📈"

    response_string = "大盤 {name} \n大盤指數 : {realPrice:.2f} \t{priceRise:.2f}% {uplow} ".format(
        name=tse_info[-1].n,
        realPrice=float(real_time),
        priceRise=rise,
        uplow=up_low)

    await update.message.reply_text(response_string)


async def update_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    fetchCode.update_codes()
    await update.message.reply_text("更新完成")


app.add_handler(CommandHandler("start", start))  # 把此 Handler 加入派送任務中
app.add_handler(CommandHandler("price", quoted))
app.add_handler(CommandHandler("odd_price", odd_quoted))
app.add_handler(CommandHandler("tse", tse))
app.add_handler(CommandHandler("updateCsv", update_csv))

app.run_polling()  # 開始推送任務


# updater.stop()  # 停止推送任務


