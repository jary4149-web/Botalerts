import os, time, requests, threading
from flask import Flask
from datetime import datetime, timedelta, timezone
A=os.getenv("TELEGRAM_TOKEN")
B=os.getenv("TELEGRAM_CHAT_ID")
G="https://api.geckoterminal.com/api/v2"
S=["NVDA","TSLA","AAPL","MSFT","AMZN","GOOGL","META","AMD","NFLX","SPY","QQQ","MSTR","HOOD","COIN","BA","BABA","NVO","PLTR","VOO","GOOG"]
seen={}
def tg(t,cid=None,kb=None):
 c=cid or B
 if not c or not A:return
 try:
  d={"chat_id":c,"text":t,"parse_mode":"Markdown","disable_web_page_preview":True}
  if kb:d["reply_markup"]=kb
  requests.post(f"https://api.telegram.org/bot{A}/sendMessage",json=d,timeout=10)
 except:pass
def loop():
 o=0
 while True:
  try:
   r=requests.get(f"https://api.telegram.org/bot{A}/getUpdates?offset={o}&timeout=15",timeout=20).json()
   for u in r.get("result",[]):
    o=u["update_id"]+1
    if "message" in u and "/start" in u["message"].get("text",""):
     ch=u["message"]["chat"]["id"]
     btns=[{"text":x,"callback_data":x} for x in S]
     rows=[]
     for i in range(0,len(btns),2):
      rows.append([btns[i],btns[i+1]] if i+1<len(btns) else [btns[i]])
     tg(f"BOT 20 xSTOCKS LIVE\n{', '.join(S)}",cid=ch,kb={"inline_keyboard":rows})
    if "callback_query" in u:
     q=u["callback_query"]
     try:requests.post(f"https://api.telegram.org/bot{A}/answerCallbackQuery",json={"callback_query_id":q["id"]},timeout=5)
     except:pass
     tg(f"{q.get('data','')} ON",cid=q["message"]["chat"]["id"])
  except:time.sleep(5)
def scan():
 while True:
  try:
   data=requests.get(f"{G}/networks/robinhood/pools?sort=created_at_desc&page=1",timeout=15).json().get("data",[])
   for p in data:
    a=p.get("attributes",{});pid=p.get("id","").split("_")[-1];name=a.get("name","")
    if not any(x in name.upper() for x in S):continue
    try:usd=float(a.get("reserve_in_usd") or 0)
    except:continue
    if usd<6000 or usd>80000:continue
    ts=a.get("pool_created_at")
    if not ts:continue
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(ts.replace("Z","+00:00"))).total_seconds()/60
    if age<10 or age>1080:continue
    h1=a.get("transactions",{}).get("h1",{});m5=a.get("transactions",{}).get("m5",{})
    bh=int(h1.get("buys",0));sh=int(h1.get("sells",0));bm=int(m5.get("buys",0))
    vh=float(a.get("volume_usd",{}).get("h1",0));vm=float(a.get("volume_usd",{}).get("m5",0))
    if sh==0:sh=1
    if bh<20 or bh<sh*2.5 or vh<1000 or bm<10:continue
    if vh>0 and vm<(vh/12*2):continue
    try:ca=p.get("relationships",{}).get("base_token",{}).get("data",{}).get("id","").split("_")[-1]
    except:ca=pid
    if not ca.startswith("0x"):ca=pid
    if ca in seen and datetime.now()-seen[ca]<timedelta(hours=6):continue
    sc=min(bh*2,40)+min((bh/max(sh,1))*10,30)+min(vm/100,30)
    if sc<75:continue
    link=f"https://www.geckoterminal.com/robinhood/pools/{pid}"
    tg(f"JOYA {name}\n${usd:.0f} Buys {bh}/{sh} Vol5m ${vm:.0f} {int(age)}m SCORE {int(sc)}\n{link}\n`{ca}`")
    seen[ca]=datetime.now()
   time.sleep(20)
  except Exception as e:print(e);time.sleep(30)
app=Flask(__name__)
@app.route("/")
def home():return "OK"
threading.Thread(target=scan,daemon=True).start()
threading.Thread(target=loop,daemon=True).start()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
