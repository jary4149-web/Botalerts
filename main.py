import os, time, requests, threading
from flask import Flask
from datetime import datetime, timedelta, timezone

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GECKO_API = "https://api.geckoterminal.com/api/v2"
TOKENIZED_STOCKS = ["NVDA","TSLA","AAPL","MSFT","AMZN","GOOGL","META","AMD","NFLX","SPY","QQQ","MSTR","HOOD","COIN","BA","BABA","NVO","PLTR","VOO","GOOG"]
alerted_cas = {}

def send_telegram(msg, chat_id=None, reply_markup=None):
    if not TELEGRAM_TOKEN: return
    cid = chat_id or TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": cid, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
    if reply_markup: payload["reply_markup"] = reply_markup
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def send_telegram_ca(ca, chat_id=None):
    cid = chat_id or TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": cid, "text": f"`{ca}`", "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def handle_telegram():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=20"
            r = requests.get(url, timeout=25).json()
            for upd in r.get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd and upd["message"].get("text","").startswith("/start"):
                    chat = upd["message"]["chat"]["id"]
                    btns = [{"text": f"📈 {s}", "callback_data": f"info_{s}"} for s in TOKENIZED_STOCKS]
                    kb = []
                    for i in range(0, len(btns), 2):
                        if i+1 < len(btns): kb.append([btns[i], btns[i+1]])
                        else: kb.append([btns[i]])
                    markup = {"inline_keyboard": kb}
                    send_telegram(f"🤖 *BOT 20 xSTOCKS ACTIVO*\n\nMonitoreando {len(TOKENIZED_STOCKS)}:\n{', '.join(TOKENIZED_STOCKS)}\n\nToca una para verificar:", chat_id=chat, reply_markup=markup)
                if "callback_query" in upd:
                    cq = upd["callback_query"]; chat = cq["message"]["chat"]["id"]
                    sym = cq.get("data","").replace("info_","")
                    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=10)
                    except: pass
                    send_telegram(f"✅ *{sym}* activa. Alertas automaticas ON.", chat_id=chat)
        except Exception as e: print(e); time.sleep(5)

def check_pools():
    while True:
        try:
            r = requests.get(f"{GECKO_API}/networks/robinhood/pools?sort=created_at_desc&page=1", timeout=15).json()
            pools = r.get('data', [])
            for pool in pools:
                attrs = pool.get('attributes', {}); pool_address = pool.get('id','').split('_')[-1]
                name = attrs.get('name',''); created_at_str = attrs.get('pool_created_at')
                reserve_usd = float(attrs.get('reserve_in_usd') or 0)
                txs = attrs.get('transactions', {}); h1 = txs.get('h1', {}); m5 = txs.get('m5', {})
                buys_h1 = int(h1.get('buys',0)); sells_h1 = int(h1.get('sells',0)); buys_m5 = int(m5.get('buys',0))
                volume = attrs.get('volume_usd', {}); vol_h1 = float(volume.get('h1',0)); vol_m5 = float(volume.get('m5',0))
                if not any(t in name.upper() for t in TOKENIZED_STOCKS): continue
                if reserve_usd < 6000 or reserve_usd > 80000: continue
                if not created_at_str: continue
                created_at = datetime.fromisoformat(created_at_str.replace('Z','+00:00'))
                age_minutes = (datetime.now(timezone.utc) - created_at).total_seconds()/60
                if age_minutes < 10 or age_minutes > 18*60: continue
                if sells_h1==0: sells_h1=1
                if buys_h1<20 or buys_h1 < (sells_h1*2.5) or vol_h1<1000 or buys_m5<10: continue
                if vol_h1>0 and vol_m5 < (vol_h1/12*2): continue
                try:
                    base_token = pool.get('relationships',{}).get('base_token',{}).get('data',{}).get('id','')
                    ca = base_token.split('_')[-1]
                    if not ca.startswith('0x'): ca = pool_address
                except: ca = pool_address
                if ca in alerted_cas and datetime.now() - alerted_cas[ca] < timedelta(hours=6): continue
                score = 0; score+=min(buys_h1*2,40); ratio=buys_h1/max(sells_h1,1); score+=min(ratio*10,30); score+=min(vol_m5/100,30); score=min(score,100)
                if score<75: continue
                gecko_link = f"https://www.geckoterminal.com/robinhood/pools/{pool_address}"
                msg = f"🚀 *NUEVA JOYA xSTOCK DETECTADA* 🚀\n\n*Pool:* {name}\n*Liquidez:* ${reserve_usd:.0f}\n*Buys 1h:* {buys_h1} | *Sells:* {sells_h1} | *Ratio:* {ratio:.1f}x\n*Vol 5m:* ${vol_m5:.0f}\n*Edad:* {int(age_minutes)} min\n*SCORE:* {score}/100\n\n{gecko_link}"
                send_telegram(msg); time.sleep(1); send_telegram_ca(ca)
                alerted_cas[ca]=datetime.now()
            time.sleep(20)
        except Exception as e: print(f"Error: {e}"); time.sleep(30)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot 20 xStocks Activo - OK"
threading.Thread(target=check_pools, daemon=True).start()
threading.Thread(target=handle_telegram, daemon=True).start()
if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
