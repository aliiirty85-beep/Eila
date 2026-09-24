from __future__ import annotations
from pathlib import Path
import asyncio, json, os, re, time
from fastapi import FastAPI
from pydantic import BaseModel

from .storage import Storage
from .ai_router import AIRouter
from .command_bus import CommandBus
from .microgoals import MicroGoalEngine
from .return_contracts import ReturnContractManager
from .engagement import EngagementEngine
from .constitution import EILA_CONSTITUTION

BASE=Path(__file__).resolve().parent.parent
DATA=BASE/"data"; DATA.mkdir(exist_ok=True)
CFG=json.loads((BASE/"config.json").read_text(encoding="utf-8"))
STORAGE=Storage(DATA/"eila.db"); STORAGE.init()
def db(): return STORAGE.connect()

AI=AIRouter(CFG)
BUS=CommandBus(db)
MICRO=MicroGoalEngine(db,CFG.get("microgoal_default_seconds",60))
RETURNS=ReturnContractManager(db,BUS,CFG)
ENG=EngagementEngine()
CURRENT={"session_id":None,"goal":"","plan":"","started_at":None}
STATE={"attention":"unknown","flow":False,"risk":"low","last_intervention":"","theme":ENG.daily_theme}

app=FastAPI(title="Eila Legend v1.0 LTS")

EILA_SYSTEM="""تو ایلا هستی؛ مربی مطالعه همیشه‌حاضر، گرم، دقیق و در اجرا محکم.
در هر لحظه فقط یک micro-goal فعال یا WAIT روشن داشته باش.
هویت ثابت است ولی شکل مأموریت‌ها تازه می‌ماند.
جذابیت فقط وقتی ارزش دارد که Recall/دقت را بهتر کند.
وقتی Flow واقعی خوب است، کمتر حرف بزن.
Gaze ذهن‌خوانی نیست؛ از آن فقط به‌عنوان سیگنال زمان‌بندی استفاده کن.
""" + EILA_CONSTITUTION

class StartReq(BaseModel):
    goal:str=""
    plan:str=""

class MicroReq(BaseModel):
    instruction:str
    kind:str="study"
    question:str=""
    expected:str=""
    seconds:int|None=None

class FeedbackReq(BaseModel):
    answer:str=""
    status:str="done"
    note:str=""

class ReturnReq(BaseModel):
    text:str="برگشت به مطالعه"
    minutes:float|None=None
    due_at:int|None=None

class AckReq(BaseModel):
    contract_id:int|None=None

class ChatReq(BaseModel):
    message:str

@app.on_event("startup")
async def startup():
    asyncio.create_task(background_loop())
    c=db()
    r=c.execute("select * from sessions where ended_at is null order by id desc limit 1").fetchone()
    c.close()
    if r:
        CURRENT.update({"session_id":r["id"],"goal":r["goal"] or "","plan":r["plan"] or "","started_at":r["started_at"]})
        MICRO.restore(int(r["id"]))

async def background_loop():
    while True:
        try:
            RETURNS.tick()
            MICRO.tick()
        except Exception:
            pass
        await asyncio.sleep(5)

@app.get("/")
def root():
    return {
      "name":"Eila","version":CFG.get("version"),"protocol_version":CFG.get("protocol_version",1),
      "session":CURRENT,"microgoal":MICRO.public(),"return_contract":RETURNS.active(),
      "theme":ENG.daily_theme,"storage":STORAGE.integrity()
    }

@app.get("/api/health")
def health():
    return {"ok":STORAGE.integrity().get("ok",False),"database":STORAGE.integrity(),"ai":AI.health()}

@app.post("/api/session/start")
def start_session(r:StartReq):
    if CURRENT["session_id"]:
        return {"ok":True,"session":CURRENT,"reason":"already-active"}
    now=int(time.time()); c=db()
    cur=c.execute("insert into sessions(started_at,goal,plan) values(?,?,?)",(now,r.goal,r.plan))
    c.commit(); sid=int(cur.lastrowid); c.close()
    CURRENT.update({"session_id":sid,"goal":r.goal,"plan":r.plan,"started_at":now})
    return {"ok":True,"session":CURRENT}

@app.post("/api/session/stop")
def stop_session():
    sid=CURRENT["session_id"]
    if sid:
        c=db(); c.execute("update sessions set ended_at=? where id=?",(int(time.time()),sid)); c.commit(); c.close()
    CURRENT.update({"session_id":None,"goal":"","plan":"","started_at":None})
    MICRO.current=None
    return {"ok":True}

@app.post("/api/micro/start")
def micro_start(r:MicroReq):
    if not CURRENT["session_id"]:
        return {"ok":False,"reason":"start-session-first"}
    style=ENG.choose_style(r.kind)
    secs=r.seconds or CFG.get("microgoal_default_seconds",60)
    w=ENG.wrap(r.instruction,style,secs,MICRO.streak)
    g=MICRO.start(CURRENT["session_id"],r.instruction,r.kind,r.question,r.expected,
                  "manual",secs,style,w["display_instruction"],w["salience"])
    BUS.queue("cache_microgoal",g,ttl_seconds=3600)
    return {"ok":True,"microgoal":g,"theme":w["theme"]}

@app.post("/api/micro/feedback")
def micro_feedback(r:FeedbackReq):
    result=MICRO.feedback(r.answer,r.status,r.note)
    if result.get("ok"):
        result["consequence"]=ENG.feedback(result["passed"],result.get("style",""),result.get("streak",0))
    return result

@app.post("/api/return/start")
def return_start(r:ReturnReq):
    try:
        return {"ok":True,"contract":RETURNS.create(r.text,r.minutes,r.due_at)}
    except Exception as e:
        return {"ok":False,"reason":str(e)}

@app.post("/api/return/ack")
def return_ack(r:AckReq):
    return RETURNS.acknowledge(r.contract_id)

@app.get("/api/device/{device_id}/commands")
def commands(device_id:str):
    return {"commands":BUS.pending(device_id)}

@app.post("/api/device/{device_id}/commands/{command_id}/ack")
def command_ack(device_id:str,command_id:int):
    BUS.ack(command_id,device_id)
    return {"ok":True}

@app.post("/api/chat")
async def chat(r:ChatReq):
    context={
      "goal":CURRENT["goal"],"plan":CURRENT["plan"],
      "microgoal":MICRO.public(),"return_contract":RETURNS.active(),
      "theme":ENG.daily_theme
    }
    txt=await AI.ask("fast",[
      {"role":"system","content":EILA_SYSTEM},
      {"role":"user","content":json.dumps(context,ensure_ascii=False)+"\nپیام کاربر: "+r.message}
    ])
    if txt.startswith("__AI_ERROR__"):
        txt="مغز زبانی در دسترس نیست؛ قراردادها، micro-goal و حافظه محلی ادامه دارند."
    return {"text":txt}

@app.post("/api/backup")
def backup():
    return {"ok":True,"path":STORAGE.backup(DATA/"backups",CFG.get("backup_keep",14))}
