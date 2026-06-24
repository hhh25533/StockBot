import os
import requests

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def get_us_stock_quote(symbol):
    # 於函式內讀取，避免 import 時機早於 load_dotenv 而取到 None
    api_key = os.getenv('FINNHUB_API_KEY')
    if not api_key:
        return "尚未設定 FINNHUB_API_KEY"

    symbol = str(symbol).strip().upper()
    if not symbol:
        return "請輸入美股代號，例如 /usprice AAPL"

    try:
        quote_res = requests.get(
            "{0}/quote".format(FINNHUB_BASE_URL),
            params={'symbol': symbol, 'token': api_key},
            timeout=10)
        quote_res.raise_for_status()
        quote = quote_res.json()
    except requests.exceptions.RequestException:
        # 不回傳原始例外，避免在訊息中洩漏帶有 token 的 URL
        return "查詢 {0} 失敗，請稍後再試".format(symbol)

    # finnhub 對無效代號的所有數值回傳 0
    if not quote.get('c'):
        return "查無此代號，請確認輸入代號"

    name = ""
    try:
        profile_res = requests.get(
            "{0}/stock/profile2".format(FINNHUB_BASE_URL),
            params={'symbol': symbol, 'token': api_key},
            timeout=10)
        profile_res.raise_for_status()
        name = profile_res.json().get('name', "")
    except requests.exceptions.RequestException:
        # 公司名稱取不到不影響報價，留空即可
        name = ""

    return {
        'symbol': symbol,
        'name': name,
        'c': quote.get('c'),
        'o': quote.get('o'),
        'pc': quote.get('pc'),
        'd': quote.get('d'),
        'dp': quote.get('dp'),
    }


def generate_us_response(data):
    rise = float(data.get('dp') or 0)
    up_low = ""
    if rise < 0:
        up_low = "📉"
    if rise > 0:
        up_low = "📈"

    response_string = "{symbol} {name} 開盤：{openPrice:.2f} \n當前價 : {realPrice:.2f} \t{priceRise:.2f}% {uplow} " \
        .format(
        symbol=data.get('symbol'),
        name=data.get('name') or "",
        openPrice=float(data.get('o') or 0),
        realPrice=float(data.get('c') or 0),
        priceRise=rise,
        uplow=up_low)

    return response_string
