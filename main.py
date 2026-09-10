import os, time, requests, threading
from flask import Flask
from datetime import datetime, timedelta, timezone
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GECKO_API = "https://api.geckoterminal.com/api/v2"
STOCKS = ["NVDA","TSLA","AAPL","MSFT","AMZN","GOOGL","META","AMD","NFLX","SPY","QQQ","MSTR","HOOD","COIN","BA","BABA","NVO","PLTR","VOO","GOOG"]
seen = {}
def tg(text, cid=None, kb=None):
 c = cid or TELEGRAM_CHAT_ID
 if not c: return
 try:
  d={"chat_id":c,"text":text,"parse_mode":"Markdown","disable_web_page_preview":True}
  if kb: d["reply_markup"]=kb
  requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json=d, timeout=10)
 except: pass
def tg_loop():
 off=0
 while True:
  try:
   r=requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={off}&timeout=15", timeout=20).json()
   for u in r.get("result",[]):
    off=u["update_id"]+1
    if "message" in u and "/start" in u["message"].get("text",""):
     chat=u["message"]["chat"]["id"]
     btns=[{"text":s,"callback_data":s} for s in STOCKS]
     rows=[]
     for i in range(0,len(btns),2):
      if i+1 < len(btns): rows.append([btns[i],btns[i+1]])
      else: rows.append([btns[i]])
     tg(f"BOT 20 xSTOCKS LIVE\nMonitoreando: {', '.join(STOCKS)}\n\nToca:", cid=chat, kb={"inline_keyboard":rows})
    if "callback_query" in u:
     q=u["callback_query"]
     try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id":q["id"]}, timeout=5)
     except: pass
     tg(f"{q.get('data','')} activa. Alertas ON", cid=q["message"]["chat"]["id"])
  except: time.sleep(5)
def scan():
 while True:
  try:
   data=requests.get(f"{GECKO_API}/networks/robinhood/pools?sort=created_at_desc&page=1", timeout=15).json().get("data",[])
   for p in data:
    a=p.get("attributes",{}); pid=p.get("id","").split("_")[-1]; name=a.get("name","")
    if not any(s in name.upper() for s in STOCKS): continue
    try: usd=float(a.get("reserve_in_usd") or 0)
    except: continue
    if usd<6000 or usd>80000: continue
    ts=a.get("pool_created_at")
    if not ts: continue
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(ts.replace("Z","+00:00"))).total_seconds()/60
    if age<10 or age>1080: continue
    h1=a.get("transactions",{}).get("h1",{}); m5=a.get("transactions",{}).get("m5",{})
    bh=int(h1.get("buys",0)); sh=int(h1.get("sells",0)); bm=int(m5.get("buys",0))
    vh=float(a.get("volume_usd",{}).get("h1",0)); vm=float(a.get("volume_usd",{}).get("m5",0))
    if sh==0: sh=1
    if bh<20 or bh < sh*2.5 or vh<1000 or bm<10: continue
    if vh>0 and vm < (vh/12*2): continue
    try: ca=p.get("relationships",{}).get("base_token",{}).get("data",{}).get("id","").split("_")[-1]
    except: ca=pid
    if not ca.startswith("0x"): ca=pid
    if ca in seen and datetime.now()-seen[ca] < timedelta(hours=6): continue
    score=min(bh*2,40)+min((bh/max(sh,1))*10,30)+min(vm/100,30)
    if score<75: continue
    link=f"https://www.geckoterminal.com/robinhood/pools/{pid}"
    tg(f"NUEVA JOYA {name}\nLiq ${usd:.0f} Buys {bh}/{sh} Vol5m ${vm:.0f} Edad {int(age)}m SCORE {int(score)}\n{link}\n\n`{ca}`")
    seen[ca]=datetime.now()
   time.sleep(20)
  except Exception as e: print(e); time.sleep(30)
app=Flask(__name__)
@app.route("/")
def home(): return "OK"
threading.Thread(target=scan, daemon=True).start()
threading.Thread(target=tg_loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
