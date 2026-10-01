import json
from types import SimpleNamespace
import requests
import readCSV
from pathlib import Path

PACKAGE_DIRECTORY = Path.cwd().parent.joinpath('docs')
TPEX_EQUITIES_CSV_PATH = PACKAGE_DIRECTORY.joinpath('tpex_equities.csv')
TWSE_EQUITIES_CSV_PATH = PACKAGE_DIRECTORY.joinpath('twse_equities.csv')

STOCK_NOT_FOUND_MESSAGE = "查無此代號，請確認輸入代號"
PRICE_UNAVAILABLE_MESSAGE = "目前無法取得成交價（可能為非交易時段），請於交易時間再查詢"


def get_stock(stock_id):
    if not str(stock_id).isnumeric():
        stock = readCSV.read_csv(TWSE_EQUITIES_CSV_PATH, stock_id)
        if stock == "" or stock is None:
            stock = readCSV.read_csv(TPEX_EQUITIES_CSV_PATH, stock_id)
            if stock == "" or stock is None: return STOCK_NOT_FOUND_MESSAGE
    else:
        stock = stock_id

    url = "https://mis.twse.com.tw/stock/api/getStock.jsp?ch={stock}.tw".format(stock=stock)
    res = requests.get(url)
    response_json = json.dumps(res.json())
    stock_key = json.loads(response_json, object_hook=lambda d: SimpleNamespace(**d))

    return stock_key


def _get_real_time_records(stock_id, info_url_template):
    stock_key = get_stock(stock_id)
    if isinstance(stock_key, str):
        return stock_key
    # TWSE 回錯誤封包（例如只有 rtcode）時沒有 msgArray，一律視為查無，不讓 AttributeError 冒出去
    stock_msgs = get_field(stock_key, "msgArray")
    if not stock_msgs or get_field(stock_msgs[-1], "key") is None:
        return STOCK_NOT_FOUND_MESSAGE

    res = requests.get(info_url_template.format(stock_msgs[-1].key))
    info = json.loads(json.dumps(res.json()), object_hook=lambda d: SimpleNamespace(**d))

    info_msgs = get_field(info, "msgArray")
    if not info_msgs:
        return STOCK_NOT_FOUND_MESSAGE

    return info_msgs


def get_real_time_stock(stock_id):
    return _get_real_time_records(stock_id, "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={0}")


def get_real_time_odd(stock_id):
    return _get_real_time_records(stock_id, "https://mis.twse.com.tw/stock/api/getOddInfo.jsp?ex_ch={0}")


def get_real_time_tse():
    url = "https://mis.twse.com.tw/stock/data/mis_ohlc_TSE.txt"
    response = requests.get(url)
    response_json = json.dumps(response.json())
    tse = json.loads(response_json, object_hook=lambda d: SimpleNamespace(**d))

    return tse.infoArray


def get_field(record, name, default=None):
    """TWSE 回傳的欄位依時段而異（例如非交易時段沒有買賣價），缺欄位時回傳 default 而不是拋 AttributeError。"""
    return getattr(record, name, default)


def to_float(value):
    """無法轉成數字（缺欄位、"-"、空字串）時回傳 None。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rise_emoji(rise):
    if rise < 0:
        return "📉"
    if rise > 0:
        return "📈"
    return ""


def generate_response(stock_info):
    if not stock_info:
        return PRICE_UNAVAILABLE_MESSAGE
    record = stock_info[-1]
    buy_price = get_field(record, "b")
    sale_price = get_field(record, "a")
    real_time_price = get_field(record, "z")
    up_low = ""
    # 買賣價都是 "-"（停牌、無任何委託）時沒有可信的行情，不能落進漲停分支
    if buy_price == "-" and sale_price == "-":
        return PRICE_UNAVAILABLE_MESSAGE
    if buy_price == "-":
        real_time_price = get_field(record, "w")
    if sale_price == "-":
        up_low = "🎊"
        real_time_price = get_field(record, "u")
    if real_time_price == "-":
        real_time_price = sale_price.split("_")[0] if isinstance(sale_price, str) else None

    real_time_price = to_float(real_time_price)
    yesterday_price = to_float(get_field(record, "y"))
    if not real_time_price or not yesterday_price:
        return PRICE_UNAVAILABLE_MESSAGE

    open_price = to_float(get_field(record, "o"))
    rise = ((real_time_price - yesterday_price) / yesterday_price) * 100
    # 跌時以 📉 取代 🎊，漲時附加 📈，持平時維持原樣
    up_low = rise_emoji(rise) if rise < 0 else up_low + rise_emoji(rise)

    return "{id} {name} 開盤：{openPrice} \n當盤成交價 : {realPrice:.2f} \t{priceRise:.2f}% {uplow} " \
        .format(
        id=get_field(record, "c", ""),
        name=get_field(record, "n", ""),
        openPrice="-" if open_price is None else "{:.2f}".format(open_price),
        realPrice=real_time_price,
        priceRise=rise,
        uplow=up_low)


def generate_tse_response(tse_info):
    if not tse_info:
        return PRICE_UNAVAILABLE_MESSAGE
    record = tse_info[-1]
    real_time = to_float(get_field(record, "z"))
    yesterday_price = to_float(get_field(record, "y"))
    if not real_time or not yesterday_price:
        return PRICE_UNAVAILABLE_MESSAGE

    rise = ((real_time - yesterday_price) / yesterday_price) * 100

    return "大盤 {name} \n大盤指數 : {realPrice:.2f} \t{priceRise:.2f}% {uplow} ".format(
        name=get_field(record, "n", ""),
        realPrice=real_time,
        priceRise=rise,
        uplow=rise_emoji(rise))
