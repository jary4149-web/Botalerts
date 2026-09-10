import os, time, requests, threading, asyncio
from flask import Flask
from datetime import datetime, timedelta, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GECKO_API = "https://api.geckoterminal.com/api/v2"
TOKENIZED_STOCKS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "AMD", "NFLX", "SPY", "QQQ", "MSTR", "HOOD", "COIN", "BA", "BABA", "NVO", "PLTR", "VOO", "GOOG"]
alerted_cas = {}

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def send_telegram_ca(ca):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": f"`{ca}`", "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [InlineKeyboardButton(f"📈 {s}", callback_data=f"info_{s}") for s in TOKENIZED_STOCKS]
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🤖 BOT 20 xSTOCKS ACTIVO\n\nMonitoreando: {', '.join(TOKENIZED_STOCKS)}\n\nToca una para verificar:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data.replace("info_", "")
    await query.message.reply_text(f"✅ {symbol} monitoreada. Alertas automáticas activas.")

def run_telegram_bot():
    async def run():
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_callback))
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True: await asyncio.sleep(3600)
    asyncio.run(run())

def check_pools():
    while True:
        try:
            r = requests.get(f"{GECKO_API}/networks/robinhood/pools?sort=created_at_desc&page=1", timeout=15).json()
            pools = r.get('data', [])
            for pool in pools:
                attrs = pool.get('attributes', {}); pool_address = pool.get('id', '').split('_')[-1]
                name = attrs.get('name', ''); created_at_str = attrs.get('pool_created_at')
                reserve_usd = float(attrs.get('reserve_in_usd') or 0)
                txs = attrs.get('transactions', {}); h1 = txs.get('h1', {}); m5 = txs.get('m5', {})
                buys_h1 = int(h1.get('buys', 0)); sells_h1 = int(h1.get('sells', 0)); buys_m5 = int(m5.get('buys', 0))
                volume = attrs.get('volume_usd', {}); vol_h1 = float(volume.get('h1', 0)); vol_m5 = float(volume.get('m5', 0))
                if not any(t in name.upper() for t in TOKENIZED_STOCKS): continue
                if reserve_usd < 6000 or reserve_usd > 80000: continue
                if not created_at_str: continue
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                age_minutes = (datetime.now(timezone.utc) - created_at).total_seconds() / 60
                if age_minutes < 10 or age_minutes > 18*60: continue
                if sells_h1 == 0: sells_h1 = 1
                if buys_h1 < 20: continue
                if buys_h1 < (sells_h1 * 2.5): continue
                if vol_h1 < 1000: continue
                if vol_h1 > 0 and vol_m5 < (vol_h1 / 12 * 2): continue
                if buys_m5 < 10: continue
                try:
                    base_token = pool.get('relationships', {}).get('base_token', {}).get('data', {}).get('id', '')
                    ca = base_token.split('_')[-1]
                    if not ca.startswith('0x'): ca = pool_address
                except: ca = pool_address
                if ca in alerted_cas and datetime.now() - alerted_cas[ca] < timedelta(hours=6): continue
                score = 0; score += min(buys_h1*2, 40); ratio = buys_h1 / max(sells_h1,1); score += min(ratio*10, 30); score += min(vol_m5/100, 30); score = min(score,100)
                if score < 75: continue
                gecko_link = f"https://www.geckoterminal.com/robinhood/pools/{pool_address}"
                msg = f"🚀 *NUEVA JOYA xSTOCK DETECTADA* 🚀\n\n*Pool:* {name}\n*Liquidez:* ${reserve_usd:.0f}\n*Buys 1h:* {buys_h1} | *Sells:* {sells_h1} | *Ratio:* {ratio:.1f}x\n*Vol 5m:* ${vol_m5:.0f} | *Vol 1h:* ${vol_h1:.0f}\n*Edad:* {int(age_minutes)} min\n*SCORE:* {score}/100\n\n{gecko_link}"
                send_telegram(msg); time.sleep(1); send_telegram_ca(ca)
                alerted_cas[ca] = datetime.now()
            time.sleep(20)
        except Exception as e: print(f"Error: {e}"); time.sleep(30)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot 20 xStocks Activo - OK"
threading.Thread(target=check_pools, daemon=True).start()
threading.Thread(target=run_telegram_bot, daemon=True).start()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
