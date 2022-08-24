import telegram
from telegram.ext import Updater, CommandHandler
import json
import configparser
from types import SimpleNamespace
import requests
import readCSV
from pathlib import Path
import fetchCode

# Load data from config.ini file
config = configparser.ConfigParser()
config.read('config.ini')

PACKAGE_DIRECTORY = Path.cwd().parent.joinpath('docs')
TPEX_EQUITIES_CSV_PATH = PACKAGE_DIRECTORY.joinpath('tpex_equities.csv')
TWSE_EQUITIES_CSV_PATH = PACKAGE_DIRECTORY.joinpath('twse_equities.csv')


updater = Updater(token=config['TELEGRAM']['ACCESS_TOKEN'], use_context=True)

dispatcher = updater.dispatcher

# 傳送訊息給使用者
def start(update, context):context.bot.send_message(chat_id=update.effective_chat.id, text="歡迎使用股票報價系統 \n 基本使用方法:\n 1. /price 股票代號 (查詢股價)\n 2. /tse 大盤指數")
#def quoted(update, context):context.bot.send_message(chat_id=update.effective_chat.id, text="請輸入股票代號")
def quoted(update, context):
    # 限制只有特定人才能新增語錄
    # if update.message.from_user.id == YOUR_USER_ID_HERE:
    if True:
        stockId = update.message.text[7:].replace('\n', ' ')
        stockInfo = getRealTimeStock(stockId)
        upLow = ""
        if isinstance(stockInfo, str):
            return update.message.reply_text(stockInfo)

        buyPrice = stockInfo[-1].b
        salsePrice = stockInfo[-1].a

        realTimePrice = stockInfo[-1].z
        openPrice = stockInfo[-1].o
        yesterdayPrice = stockInfo[-1].y

        if buyPrice == "-":
            realTimePrice = stockInfo[-1].w
        
        if salsePrice == "-":
            upLow = "🎊"
            realTimePrice = stockInfo[-1].u
        
        print(realTimePrice)
        print(yesterdayPrice)

        rise = ((float(realTimePrice) - float(yesterdayPrice)) / float(yesterdayPrice)) * 100
        
        print(rise)

        
        if rise < 0:
            upLow = "📉"
        if rise > 0:
            upLow += "📈"

        reStr = "{id} {name} 開盤：{openPrice:.2f} \n當盤成交價 : {realPrice:.2f} \t{priceRise:.2f}% {uplow} ".format(id=stockInfo[-1].c,name=stockInfo[-1].n,openPrice=float(openPrice),realPrice=float(realTimePrice),priceRise=rise,uplow=upLow)

        update.message.reply_text(reStr)

def tse(update, context):
        tseInfo=getRealTimeTse()
        
        realTime = tseInfo[-1].z
        openPrice = tseInfo[-1].o
        yesterdayPrice = tseInfo[-1].y

        rise = ((float(realTime)-float(yesterdayPrice))/float(yesterdayPrice))*100

        upLow = ""
        if rise < 0:
            upLow = "📉"
        if rise > 0:
            upLow = "📈"

        reStr="大盤 {name} \n大盤指數 : {realPrice:.2f} \t{priceRise:.2f}% {uplow} ".format(name=tseInfo[-1].n,realPrice=float(realTime),priceRise=rise,uplow=upLow)

        update.message.reply_text(reStr)

def updateCsv(update, context):
    fetchCode.update_codes()
    update.message.reply_text("更新完成")

start_handler = CommandHandler('start', start)
quoted_handler = CommandHandler('price', quoted)
tse_handler = CommandHandler('tse', tse)
updateCsv_handler=CommandHandler('updateCsv',updateCsv)
dispatcher.add_handler(start_handler)  # 把此 Handler 加入派送任務中
dispatcher.add_handler(quoted_handler)
dispatcher.add_handler(tse_handler)
dispatcher.add_handler(updateCsv_handler)

updater.start_polling()  # 開始推送任務
# updater.stop()  # 停止推送任務

def getRealTimeStock(stockId):

    if str(stockId).isnumeric()==False:
        stock=readCSV.read_csv(TWSE_EQUITIES_CSV_PATH, stockId)
        if stock=="" or stock==None:
            stock=readCSV.read_csv(TPEX_EQUITIES_CSV_PATH, stockId)
            if stock=="" or stock==None :return "查無此代號，請確認輸入代號"
    else:
        stock=stockId

    url = "https://mis.twse.com.tw/stock/api/getStock.jsp?ch={stock}.tw".format(stock = stock)
    res = requests.get(url)
    reJson=json.dumps(res.json())
    stockKey=json.loads(reJson, object_hook=lambda d: SimpleNamespace(**d))

    if len(stockKey.msgArray)<=0:
        return "查無此代號，請確認輸入代號"

    infoUrl="https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={0}".format(stockKey.msgArray[-1].key)
    res = requests.get(infoUrl)
    stockInfo=json.loads(json.dumps(res.json()), object_hook=lambda d: SimpleNamespace(**d)) 

    if len(stockInfo.msgArray)<=0:
            return "查無此代號，請確認輸入代號"

    return stockInfo.msgArray

def getRealTimeTse():

    url = "https://mis.twse.com.tw/stock/data/mis_ohlc_TSE.txt"
    res = requests.get(url)
    reJson=json.dumps(res.json())
    tse=json.loads(reJson, object_hook=lambda d: SimpleNamespace(**d))

    return tse.infoArray





