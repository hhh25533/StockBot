import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import json
from types import SimpleNamespace
import requests
import readCSV
from pathlib import Path
import fetchCode

PACKAGE_DIRECTORY = Path.cwd().parent.joinpath('docs')
TPEX_EQUITIES_CSV_PATH = PACKAGE_DIRECTORY.joinpath('tpex_equities.csv')
TWSE_EQUITIES_CSV_PATH = PACKAGE_DIRECTORY.joinpath('twse_equities.csv')
print(os.getenv('TELEGRAM_ACCESS_TOKEN'))

app = ApplicationBuilder().token(os.getenv('TELEGRAM_ACCESS_TOKEN')).build()


# 傳送訊息給使用者
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="歡迎使用股票報價系統 \n 基本使用方法:\n 1. /price 股票代號 (查詢股價)\n 2. /tse 大盤指數"
    )


def get_real_time_stock(stock_id):
    if not str(stock_id).isnumeric():
        stock = readCSV.read_csv(TWSE_EQUITIES_CSV_PATH, stock_id)
        if stock == "" or stock is None:
            stock = readCSV.read_csv(TPEX_EQUITIES_CSV_PATH, stock_id)
            if stock == "" or stock is None: return "查無此代號，請確認輸入代號"
    else:
        stock = stock_id

    url = "https://mis.twse.com.tw/stock/api/getStock.jsp?ch={stock}.tw".format(stock=stock)
    res = requests.get(url)
    response_json = json.dumps(res.json())
    stock_key = json.loads(response_json, object_hook=lambda d: SimpleNamespace(**d))

    if len(stock_key.msgArray) <= 0:
        return "查無此代號，請確認輸入代號"

    info_url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={0}".format(stock_key.msgArray[-1].key)
    res = requests.get(info_url)
    stock_info = json.loads(json.dumps(res.json()), object_hook=lambda d: SimpleNamespace(**d))

    if len(stock_info.msgArray) <= 0:
        return "查無此代號，請確認輸入代號"

    return stock_info.msgArray


def get_real_time_tse():
    url = "https://mis.twse.com.tw/stock/data/mis_ohlc_TSE.txt"
    response = requests.get(url)
    response_json = json.dumps(response.json())
    tse = json.loads(response_json, object_hook=lambda d: SimpleNamespace(**d))

    return tse.infoArray


# def quoted(update, context):context.bot.send_message(chat_id=update.effective_chat.id, text="請輸入股票代號")
async def quoted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 限制只有特定人才能新增語錄
    # if update.message.from_user.id == YOUR_USER_ID_HERE:
    if True:
        stock_id = update.message.text[7:].replace('\n', ' ')
        stock_info = get_real_time_stock(stock_id)
        up_low = ""
        if isinstance(stock_info, str):
            await update.message.reply_text(stock_info)

        buy_price = stock_info[-1].b
        sale_price = stock_info[-1].a

        real_time_price = stock_info[-1].z
        open_price = stock_info[-1].o
        yesterday_price = stock_info[-1].y

        if buy_price == "-":
            real_time_price = stock_info[-1].w

        if sale_price == "-":
            up_low = "🎊"
            real_time_price = stock_info[-1].u

        if real_time_price == "-":
            real_time_price = stock_info[-1].a.split("_")[0]

        rise = ((float(real_time_price) - float(yesterday_price)) / float(yesterday_price)) * 100

        if rise < 0:
            up_low = "📉"
        if rise > 0:
            up_low += "📈"

        response_string = "{id} {name} 開盤：{openPrice:.2f} \n當盤成交價 : {realPrice:.2f} \t{priceRise:.2f}% {uplow} ".format(
            id=stock_info[-1].c,
            name=stock_info[-1].n,
            openPrice=float(open_price),
            realPrice=float(real_time_price),
            priceRise=rise,
            uplow=up_low)

        await update.message.reply_text(response_string)


async def tse(update: Update,  context: ContextTypes.DEFAULT_TYPE) -> None:
    tse_info = get_real_time_tse()

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
app.add_handler(CommandHandler("tse", tse))
app.add_handler(CommandHandler("updateCsv", update_csv))

app.run_polling()  # 開始推送任務


# updater.stop()  # 停止推送任務


