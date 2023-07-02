import json
from types import SimpleNamespace
import requests
import readCSV
from pathlib import Path

PACKAGE_DIRECTORY = Path.cwd().parent.joinpath('docs')
TPEX_EQUITIES_CSV_PATH = PACKAGE_DIRECTORY.joinpath('tpex_equities.csv')
TWSE_EQUITIES_CSV_PATH = PACKAGE_DIRECTORY.joinpath('twse_equities.csv')


def get_stock(stock_id):
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

    return stock_key


def get_real_time_stock(stock_id):

    stock_key = get_stock(stock_id)
    if len(stock_key.msgArray) <= 0:
        return "查無此代號，請確認輸入代號"

    info_url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={0}".format(stock_key.msgArray[-1].key)
    res = requests.get(info_url)
    stock_info = json.loads(json.dumps(res.json()), object_hook=lambda d: SimpleNamespace(**d))

    if len(stock_info.msgArray) <= 0:
        return "查無此代號，請確認輸入代號"

    return stock_info.msgArray


def get_real_time_odd(stock_id):

    stock_key = get_stock(stock_id)
    if len(stock_key.msgArray) <= 0:
        return "查無此代號，請確認輸入代號"

    info_url = "https://mis.twse.com.tw/stock/api/getOddInfo.jsp?ex_ch={0}".format(stock_key.msgArray[-1].key)
    res = requests.get(info_url)
    odd_info = json.loads(json.dumps(res.json()), object_hook=lambda d: SimpleNamespace(**d))

    if len(odd_info.msgArray) <= 0:
        return "查無此代號，請確認輸入代號"

    return odd_info.msgArray


def get_real_time_tse():
    url = "https://mis.twse.com.tw/stock/data/mis_ohlc_TSE.txt"
    response = requests.get(url)
    response_json = json.dumps(response.json())
    tse = json.loads(response_json, object_hook=lambda d: SimpleNamespace(**d))

    return tse.infoArray


def generate_response(stock_info):
    buy_price = stock_info[-1].b
    sale_price = stock_info[-1].a
    real_time_price = stock_info[-1].z
    open_price = stock_info[-1].o
    yesterday_price = stock_info[-1].y
    up_low = ""
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

    response_string = "{id} {name} 開盤：{openPrice:.2f} \n當盤成交價 : {realPrice:.2f} \t{priceRise:.2f}% {uplow} " \
        .format(
        id=stock_info[-1].c,
        name=stock_info[-1].n,
        openPrice=float(open_price),
        realPrice=float(real_time_price),
        priceRise=rise,
        uplow=up_low)

    return response_string
