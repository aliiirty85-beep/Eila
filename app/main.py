from __future__ import annotations
from pathlib import Path
import asyncio,json,time
from fastapi import FastAPI,Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field

from .storage import Storage
from .ai_router import AIRouter
from .command_bus import CommandBus
from .device_hub import DeviceHub
from .engagement import EngagementEngine
from .microgoals import MicroGoalEngine
from .return_contracts import ReturnContractManager
from .focus_engine import FocusEngine
from .learning import LearningPulse
from .integrity import StudyIntegrity
from .memory import MemoryManager
from .context import ContextRegistry
from .screen_context import ScreenContext
from .question_engine import QuestionEngine
from .web_brain import WebBrain
from .rival import RivalEngine
from .constitution import EILA_CONSTITUTION
from .security import SecurityManager

BASE=Path(__file__).resolve().parent.parent
DATA=BASE/"data";DATA.mkdir(exist_ok=True)
CFG=json.loads((BASE/"config.json").read_text(encoding="utf-8"))
STORAGE=Storage(DATA/"eila.db");STORAGE.init()
SECURITY=SecurityManager(DATA)
def db():return STORAGE.connect()

AI=AIRouter(CFG);BUS=CommandBus(db);HUB=DeviceHub(db,CFG.get("device_stale_seconds",15));ENG=EngagementEngine(db)
MICRO=MicroGoalEngine(db,CFG.get("microgoal_default_seconds",60),CFG.get("microgoal_min_seconds",20),CFG.get("microgoal_max_seconds",180))
RETURNS=ReturnContractManager(db,BUS,CFG);FOCUS=FocusEngine(CFG);PULSE=LearningPulse(db);INTEGRITY=StudyIntegrity();MEM=MemoryManager(db)
CONTEXT=ContextRegistry(db);SCREEN=ScreenContext();QUESTIONS=QuestionEngine(AI,SCREEN,CONTEXT);WEB=WebBrain(db,AI,BASE,CFG)
RIVAL=RivalEngine(db,CFG.get("competition_target_multiplier",1.07))

CURRENT={"session_id":None,"goal":"","plan":"","started_at":None}
STATE={"attention_score":50.0,"attention":"unknown","flow":False,"risk":{"level":"low","risk":0},"phase":"IDLE","last_intervention":"",
       "theme":ENG.daily_theme,"learning_pulse":{},"integrity":{},"gaze_device":None,"gaze":None,"devices":[]}
LAST_BACKUP=0.0

EILA_SYSTEM=("""تو ایلا هستی؛ مربی مطالعه همیشه‌حاضر، گرم، دقیق، آرام و در اجرا محکم.
مالک هدف و تصمیم نهایی کاربر است؛ تو مدیر اجرای لحظه‌ای مطالعه هستی.
در هر لحظه فقط یک micro-goal فعال یا WAIT روشن داشته باش.
هدف‌های کوتاه را با تازگی، کنجکاوی، رقابت، فوریت یا teach-back جذاب کن، اما هرگز جذابیت را جای یادگیری واقعی نگذار.
وقتی Flow واقعی خوب است کم‌حرف شو. وقتی افت نزدیک است قبل از سقوط، مداخله کوچک و دقیق کن.
اگر کاربر گفت چند دقیقه دیگر برمی‌گردد، آن را Return Contract بدان و پیگیری فعال کن.
Gaze فقط سیگنال احتمالی است؛ ذهن‌خوانی نکن.
پاسخ‌ها در Focus Mode کوتاه و عملی باشند.
"""+EILA_CONSTITUTION)

app=FastAPI(title="Eila Legend v2.0 LTS")

@app.middleware("http")
async def lan_auth(request:Request,call_next):
    host=request.client.host if request.client else ""
    local=host in {"127.0.0.1","::1","localhost"}
    if request.url.path.startswith("/api/") and not local:
        if not SECURITY.valid(request.headers.get("X-Eila-Token")):
            from fastapi.responses import JSONResponse
            return JSONResponse({"ok":False,"reason":"pairing-token-required"},status_code=401)
    return await call_next(request)

app.mount("/static",StaticFiles(directory=BASE/"app"/"static"),name="static")

class StartReq(BaseModel):goal:str="";plan:str=""
class MicroReq(BaseModel):
    instruction:str;kind:str="study";question:str="";expected:str="";seconds:int|None=None;hook:str="";context_ref:str=""
class FeedbackReq(BaseModel):
    answer:str="";status:str="done";note:str="";confidence:float=Field(.5,ge=0,le=1);latency_ms:int=0;topic:str="";error_type:str=""
class ReturnReq(BaseModel):text:str="برگشت به مطالعه";minutes:float|None=None;due_at:int|None=None
class AckReq(BaseModel):contract_id:int|None=None
class DeviceReq(BaseModel):device_id:str;kind:str="android";name:str="";capabilities:dict={};state:dict={}
class GazeReq(BaseModel):
    device_id:str;zone:str="unknown";quality:float=.5;x:float|None=None;y:float|None=None
    study_ratio_15:float|None=None;study_ratio_60:float|None=None;away_streak_seconds:float=0
    max_fixation_seconds:float=0;jump_rate:float|None=None;event:str="";timestamp_ms:int|None=None
class ChatReq(BaseModel):message:str
class ContextReq(BaseModel):kind:str="text";title:str="";content:str="";ref:str=""
class AttentionReq(BaseModel):score:float=Field(...,ge=0,le=100);screen_change:float|None=None;input_recent:bool|None=None
class ScoreReq(BaseModel):delta:float
class MemoryReq(BaseModel):category:str;key:str;value:str;confidence:float=.6;source:str="manual"

@app.on_event("startup")
async def startup():
    restore_continuity();asyncio.create_task(background_loop())

def restore_continuity():
    c=db();r=c.execute("select * from sessions where ended_at is null order by id desc limit 1").fetchone();c.close()
    if r:
        CURRENT.update({"session_id":r["id"],"goal":r["goal"] or "","plan":r["plan"] or "","started_at":r["started_at"]})
        MICRO.restore(int(r["id"]));FOCUS.session_started=float(r["started_at"])

async def background_loop():
    global LAST_BACKUP
    while True:
        try:
            RETURNS.tick();MICRO.tick();await maybe_autogoal();await maybe_web_brain()
            now=time.time();interval=float(CFG.get("backup_interval_minutes",30))*60
            if now-LAST_BACKUP>=interval:
                STORAGE.backup(DATA/"backups",CFG.get("backup_keep",14));LAST_BACKUP=now
        except Exception as e:STATE["last_error"]=f"{type(e).__name__}: {e}"
        await asyncio.sleep(max(2,int(CFG.get("verdict_interval_seconds",5))))

async def maybe_web_brain():
    if not WEB.running:await WEB.run_once(force=False)

async def maybe_autogoal():
    if not CURRENT["session_id"] or MICRO.current:return
    gaze_device,gaze=HUB.primary_gaze()
    if not gaze:return
    event=(gaze.get("event") or "").lower()
    high_value=event in {"long_fixation","rapid_revisit","flighty","stuck"} or STATE.get("risk",{}).get("level")=="high"
    if not high_value:return
    result=await QUESTIONS.from_gaze(gaze,deep=True)
    if not result.get("ok"):return
    d=result["data"];style=ENG.choose_style(d.get("kind","study"))
    w=ENG.wrap(d.get("instruction") or d.get("question") or "همین بخش",style,d.get("seconds",60),MICRO.streak,d.get("hook",""))
    g=MICRO.start(CURRENT["session_id"],d.get("instruction") or d.get("question") or "همین بخش",d.get("kind","study"),d.get("question",""),
                  d.get("expected",""),"gaze-ai",d.get("seconds",60),style,w["display_instruction"],w["salience"],d.get("topic",""))
    BUS.queue("microgoal",g,ttl_seconds=900)

@app.get("/")
def root_ui():return FileResponse(BASE/"app"/"static"/"index.html")

@app.get("/api/state")
def state():
    STATE["devices"]=HUB.devices();STATE["theme"]=ENG.daily_theme;STATE["microgoal"]=MICRO.public();STATE["return_contract"]=RETURNS.active();STATE["session"]=CURRENT
    if CURRENT["session_id"]:STATE["rival"]=RIVAL.ensure_round(CURRENT["session_id"])
    return STATE

@app.get("/api/health")
def health():
    return {"ok":STORAGE.integrity().get("ok",False),"database":STORAGE.integrity(),"ai":AI.health(),"screen_error":SCREEN.last_error,
            "devices":HUB.devices(),"web_brain":{"last_run":WEB.last_run,"last_error":WEB.last_error}}

@app.post("/api/session/start")
def start_session(r:StartReq):
    if CURRENT["session_id"]:return {"ok":True,"session":CURRENT,"reason":"already-active"}
    now=int(time.time());c=db();cur=c.execute("insert into sessions(started_at,goal,plan) values(?,?,?)",(now,r.goal,r.plan));c.commit();sid=int(cur.lastrowid);c.close()
    CURRENT.update({"session_id":sid,"goal":r.goal,"plan":r.plan,"started_at":now});FOCUS.session_started=time.time();RIVAL.ensure_round(sid)
    return {"ok":True,"session":CURRENT}

@app.post("/api/session/stop")
def stop_session():
    sid=CURRENT["session_id"];summary=MEM.session_summary(sid) if sid else {"text":"","points":[]}
    if sid:
        c=db();c.execute("update sessions set ended_at=?,summary=? where id=?",(int(time.time()),summary["text"],sid));c.commit();c.close()
    CURRENT.update({"session_id":None,"goal":"","plan":"","started_at":None});MICRO.current=None
    return {"ok":True,"summary":summary}

@app.post("/api/micro/start")
def micro_start(r:MicroReq):
    if not CURRENT["session_id"]:return {"ok":False,"reason":"start-session-first"}
    style=ENG.choose_style(r.kind);secs=r.seconds or CFG.get("microgoal_default_seconds",60);w=ENG.wrap(r.instruction,style,secs,MICRO.streak,r.hook)
    g=MICRO.start(CURRENT["session_id"],r.instruction,r.kind,r.question,r.expected,"manual",secs,style,w["display_instruction"],w["salience"],r.context_ref)
    BUS.queue("microgoal",g,ttl_seconds=900);return {"ok":True,"microgoal":g,"theme":w["theme"]}

@app.post("/api/micro/feedback")
def micro_feedback(r:FeedbackReq):
    before=float(STATE.get("attention_score",50));result=MICRO.feedback(r.answer,r.status,r.note,r.confidence,r.latency_ms,r.topic,r.error_type)
    if result.get("ok"):
        result["consequence"]=ENG.feedback(result["passed"],result.get("style",""),result.get("streak",0))
        ENG.record_trial(result.get("style","") or "precision",result["passed"],before,float(STATE.get("attention_score",before)),r.latency_ms)
        BUS.queue("feedback",{"text":result["consequence"],"passed":result["passed"]},ttl_seconds=180)
        if CURRENT["session_id"]:RIVAL.add_user_score(CURRENT["session_id"],3 if result["passed"] else -1)
    return result

@app.post("/api/return/start")
def return_start(r:ReturnReq):
    try:return {"ok":True,"contract":RETURNS.create(r.text,r.minutes,r.due_at)}
    except Exception as e:return {"ok":False,"reason":str(e)}

@app.post("/api/return/ack")
def return_ack(r:AckReq):return RETURNS.acknowledge(r.contract_id)

@app.post("/api/device/heartbeat")
def heartbeat(r:DeviceReq):return HUB.heartbeat(r.device_id,r.kind,r.name,r.capabilities,r.state)

@app.post("/api/gaze")
def gaze(r:GazeReq):
    sample=r.model_dump();HUB.ingest_gaze(r.device_id,sample);STATE["gaze_device"]=r.device_id;STATE["gaze"]=sample;return {"ok":True}

@app.get("/api/device/{device_id}/commands")
def commands(device_id:str):return {"commands":BUS.pending(device_id)}

@app.post("/api/device/{device_id}/commands/{command_id}/ack")
def command_ack(device_id:str,command_id:int):BUS.ack(command_id,device_id);return {"ok":True}

@app.post("/api/attention")
def attention(r:AttentionReq):
    score=float(r.score);FOCUS.observe(score);_,gaze=HUB.primary_gaze();risk=FOCUS.risk(score,gaze,MICRO.public());flow=FOCUS.flow_protected(score,gaze,MICRO.public());pulse=PULSE.score(score);integrity=INTEGRITY.assess(score,gaze,r.screen_change,r.input_recent,pulse)
    phase=FOCUS.phase(score);intervention="";critical=score<28 or float((gaze or {}).get("away_streak_seconds") or 0)>=8
    if not flow and FOCUS.can_intervene(critical):
        if critical:intervention="ایلا: RETURN. فقط همین مأموریت."
        elif risk["level"]=="high":intervention="ایلا: افت نزدیکه؛ انتخاب اضافه نداریم. همین micro-goal را تحویل بده."
        if intervention:FOCUS.mark_intervention();BUS.queue("speak" if critical else "notify",{"text":intervention},ttl_seconds=120)
    STATE.update({"attention_score":score,"attention":"study" if score>=60 else ("uncertain" if score>=45 else "off-task"),"risk":risk,"flow":flow,"phase":phase,"learning_pulse":pulse,"integrity":integrity,"last_intervention":intervention})
    if CURRENT["session_id"]:
        c=db();c.execute("""insert into attention_samples(ts,session_id,device_id,score,zone,study_ratio,away_streak,fixation,jump_rate,risk,metadata)
          values(?,?,?,?,?,?,?,?,?,?,?)""",(int(time.time()),CURRENT["session_id"],STATE.get("gaze_device") or "",score,(gaze or {}).get("zone",""),(gaze or {}).get("study_ratio_15"),(gaze or {}).get("away_streak_seconds"),(gaze or {}).get("max_fixation_seconds"),(gaze or {}).get("jump_rate"),risk["level"],json.dumps(integrity,ensure_ascii=False)));c.commit();c.close()
    return STATE

@app.post("/api/context/current")
def set_context(r:ContextReq):return {"ok":True,"id":CONTEXT.set(r.kind,r.title,r.content,r.ref)}
@app.get("/api/context/current")
def get_context():return CONTEXT.current() or {}

@app.post("/api/question/from-gaze")
async def question_from_gaze():
    _,g=HUB.primary_gaze()
    if not g:return {"ok":False,"reason":"no-gaze"}
    return await QUESTIONS.from_gaze(g,deep=True)

@app.post("/api/memory")
def memory(r:MemoryReq):MEM.upsert(r.category,r.key,r.value,r.confidence,r.source);return {"ok":True}
@app.get("/api/memory")
def memories():return {"items":MEM.relevant()}
@app.get("/api/research/latest")
def research_latest():return {"items":WEB.latest()}
@app.post("/api/research/run")
async def research_run():return await WEB.run_once(force=True)
@app.post("/api/rival/score")
def rival_score(r:ScoreReq):
    if not CURRENT["session_id"]:return {"ok":False,"reason":"no-session"}
    return {"ok":True,"state":RIVAL.add_user_score(CURRENT["session_id"],r.delta)}

@app.post("/api/chat")
async def chat(r:ChatReq):
    context={"goal":CURRENT["goal"],"plan":CURRENT["plan"],"microgoal":MICRO.public(),"return_contract":RETURNS.active(),"theme":ENG.daily_theme,"state":STATE,"memory":MEM.relevant(15)}
    txt=await AI.ask("fast",[{"role":"system","content":EILA_SYSTEM},{"role":"user","content":json.dumps(context,ensure_ascii=False)+"\nپیام کاربر: "+r.message}],max_tokens=700)
    if txt.startswith("__AI_ERROR__"):txt="مغز زبانی در دسترس نیست؛ قراردادها، micro-goal، حافظه و نگهبانی پایه ادامه دارند."
    return {"text":txt}

@app.post("/api/backup")
def backup():return {"ok":True,"path":STORAGE.backup(DATA/"backups",CFG.get("backup_keep",14))}
