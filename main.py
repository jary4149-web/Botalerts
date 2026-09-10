import os, time, requests
from flask import Flask
import threading
app = Flask(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SYMBOL = "SPY"
CHECK_SECONDS = 60
last_price = None
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except: pass
def get_price():
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}).json()
        return float(r["chart"]["result"][0]["meta"]["regularMarketPrice"])
    except: return None
def bot_loop():
    global last_price
    send_telegram(f"Bot iniciado {SYMBOL}")
    while True:
        price = get_price()
        if price:
            if last_price is None: last_price = price
            if abs(price-last_price) >= 0.5:
                send_telegram(f"{SYMBOL}: ${price}")
                last_price = price
        time.sleep(CHECK_SECONDS)
@app.route("/")
def home(): return "Bot activo"
threading.Thread(target=bot_loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
