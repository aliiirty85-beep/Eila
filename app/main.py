from __future__ import annotations
from pathlib import Path
import asyncio,json,time,base64,os,platform,socket,uuid
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
from .learning import LearningPulse,LearningModel
from .integrity import StudyIntegrity
from .memory import MemoryManager,PolicyEngine,EvolutionEngine
from .context import ContextRegistry
from .screen_context import ScreenContext
from .question_engine import QuestionEngine
from .web_brain import WebBrain
from .rival import RivalEngine
from .constitution import EILA_CONSTITUTION
from .security import SecurityManager
from .future_engine import FutureEngine
from .intent_router import IntentRouter
from .firewall import StudyFirewall
from .sync import SyncManager,EventBus,SpineState
from .desktop_sensors import DesktopSensors
from .attention_fusion import AttentionFusion
from .context_verifier import ContextVerifier
from .maintenance import MaintenanceEngine

BASE=Path(__file__).resolve().parent.parent
DATA=BASE/"data";DATA.mkdir(exist_ok=True)
CFG=json.loads((BASE/"config.json").read_text(encoding="utf-8"))
STORAGE=Storage(DATA/"eila.db")
try:
    STORAGE.init()
except Exception:
    recovered=STORAGE.recover_latest_backup(DATA/"backups")
    if not recovered.get("ok"):raise
    STORAGE.init()

SECURITY=SecurityManager(DATA)
def db():return STORAGE.connect()

EVENTS=EventBus(db);SPINE=SpineState(db,EVENTS)
AI=AIRouter(CFG);BUS=CommandBus(db);HUB=DeviceHub(db,CFG.get("device_stale_seconds",15),EVENTS);ENG=EngagementEngine(db)
MICRO=MicroGoalEngine(db,CFG.get("microgoal_default_seconds",60),CFG.get("microgoal_min_seconds",20),CFG.get("microgoal_max_seconds",180))
RETURNS=ReturnContractManager(db,BUS,CFG);FOCUS=FocusEngine(CFG);PULSE=LearningPulse(db);INTEGRITY=StudyIntegrity();MEM=MemoryManager(db)
LEARN=LearningModel(db,EVENTS);POLICIES=PolicyEngine(db,EVENTS);EVOLVE=EvolutionEngine(db,AI,POLICIES)
CONTEXT=ContextRegistry(db);SCREEN=ScreenContext();QUESTIONS=QuestionEngine(AI,SCREEN,CONTEXT);WEB=WebBrain(db,AI,BASE,CFG)
RIVAL=RivalEngine(db,CFG.get("competition_target_multiplier",1.07));FUTURE=FutureEngine();INTENTS=IntentRouter();FIREWALL=StudyFirewall(db)
SYNC=SyncManager(db,MEM,CFG.get("protocol_version",3),EVENTS,SPINE);DESKTOP=DesktopSensors();FUSION=AttentionFusion()
VERIFIER=ContextVerifier(db,CFG);MAINT=MaintenanceEngine(db,STORAGE,AI,DATA,CFG)

CURRENT={"session_id":None,"goal":"","plan":"","started_at":None}
STATE={"activity_context":None,"maintenance":{},"attention_score":50.0,"attention":"unknown","flow":False,"risk":{"level":"low","risk":0},"phase":"IDLE","last_intervention":"",
       "theme":ENG.daily_theme,"learning_pulse":{},"integrity":{},"gaze_device":None,"gaze":None,"devices":[],
       "future":{"now_5s":"—","next_60s":"—","round_10m":"—"}}
LAST_BACKUP=0.0
LAST_AUTOGOAL=0.0

EILA_SYSTEM=("""تو ایلا هستی؛ مربی مطالعه همیشه‌حاضر، گرم، دقیق، آرام و در اجرا محکم.
مالک هدف و تصمیم نهایی کاربر است؛ تو مدیر اجرای لحظه‌ای مطالعه هستی.
در هر لحظه فقط یک micro-goal فعال یا WAIT روشن داشته باش.
هدف‌های کوتاه را با تازگی، کنجکاوی، رقابت، فوریت یا teach-back جذاب کن، اما هرگز جذابیت را جای یادگیری واقعی نگذار.
وقتی Flow واقعی خوب است کم‌حرف شو. وقتی افت نزدیک است قبل از سقوط، مداخله کوچک و دقیق کن.
اگر کاربر گفت چند دقیقه دیگر برمی‌گردد، آن را Return Contract بدان و پیگیری فعال کن.
Gaze فقط سیگنال احتمالی است؛ ذهن‌خوانی نکن.
در Focus Mode گفت‌وگوی حاشیه‌ای را به Later Inbox بفرست؛ سؤال درسی و مسئله فوری سلامت/زندگی را block نکن.
پاسخ‌ها در Focus Mode کوتاه و عملی باشند.
"""+EILA_CONSTITUTION)

app=FastAPI(title="Eila Spine v3")

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
class DeviceReq(BaseModel):
    device_id:str;kind:str="android";name:str="";hardware_fingerprint:str=""
    capabilities:dict=Field(default_factory=dict);state:dict=Field(default_factory=dict)
class GazeReq(BaseModel):
    device_id:str;zone:str="unknown";quality:float=.5;x:float|None=None;y:float|None=None
    study_ratio_15:float|None=None;study_ratio_60:float|None=None;away_streak_seconds:float=0
    max_fixation_seconds:float=0;jump_rate:float|None=None;event:str="";timestamp_ms:int|None=None
class ChatReq(BaseModel):message:str
class ContextReq(BaseModel):kind:str="text";title:str="";content:str="";ref:str=""
class ImageContextReq(BaseModel):title:str="صفحه کتاب";data_url:str
class AttentionReq(BaseModel):score:float=Field(...,ge=0,le=100);screen_change:float|None=None;input_recent:bool|None=None
class ScoreReq(BaseModel):delta:float
class MemoryReq(BaseModel):category:str;key:str;value:str;confidence:float=.6;source:str="manual"
class SnapshotReq(BaseModel):device_id:str;snapshot:dict=Field(default_factory=dict)
class SpineSetReq(BaseModel):value:object;source_device:str="user";expected_revision:int|None=None
class EventReq(BaseModel):event:dict=Field(default_factory=dict)
class PolicyReq(BaseModel):scope:str="study";trigger:dict=Field(default_factory=dict);action:dict=Field(default_factory=dict);priority:int=50;rationale:str=""
class PolicyRollbackReq(BaseModel):version:int
class ConflictResolveReq(BaseModel):choice:str
class EvolveReq(BaseModel):text:str
class DeviceReplaceReq(BaseModel):old_device_id:str;new_device_id:str;kind:str="laptop";name:str="";capabilities:dict=Field(default_factory=dict);hardware_fingerprint:str=""
class ActivityClaimReq(BaseModel):activity:str;minutes:float|None=None;note:str=""
class ActivityEvidenceReq(BaseModel):device_id:str="";kind:str="device";facts:dict=Field(default_factory=dict)
class BallStimulusReq(BaseModel):source:str="BallRivalAndroid";event:str;ts:int|None=None;extra:dict=Field(default_factory=dict)

@app.on_event("startup")
async def startup():
    bootstrap_spine()
    ensure_core_node()
    restore_continuity()
    asyncio.create_task(background_loop())

def ensure_core_node():
    fingerprint="|".join([platform.system(),platform.release(),platform.machine(),socket.gethostname()])
    saved=STORAGE.get_meta("core_node_identity",{}) or {}
    if saved.get("hardware_fingerprint")!=fingerprint:
        saved={"device_id":"core-"+str(uuid.uuid4()),"hardware_fingerprint":fingerprint}
        STORAGE.set_meta("core_node_identity",saved)
    kind=os.getenv("EILA_NODE_KIND","laptop" if platform.system().lower()=="windows" else "server")
    caps={"core":True,"sync":True,"desktop_sensors":True,"screen_context":True,
          "local_ai_router":True,"maintenance":True,"backup":True}
    return HUB.heartbeat(saved["device_id"],kind,socket.gethostname(),caps,
                         {"version":CFG.get("version"),"protocol":CFG.get("protocol_version",3)},
                         saved["hardware_fingerprint"])

def bootstrap_spine():
    if not SPINE.get("identity"):
        SPINE.set("identity",{"name":"Eila","identity_version":1,"role":"persistent-study-companion"},"core")
    if not SPINE.get("architecture"):
        SPINE.set("architecture",{"mode":"device-independent","laptop_role":"replaceable-compute-node","protocol":CFG.get("protocol_version",3)},"core")

def restore_continuity():
    c=db();r=c.execute("select * from sessions where ended_at is null order by id desc limit 1").fetchone();c.close()
    if r:
        CURRENT.update({"session_id":r["id"],"goal":r["goal"] or "","plan":r["plan"] or "","started_at":r["started_at"]})
        MICRO.restore(int(r["id"]));FOCUS.session_started=float(r["started_at"])

async def background_loop():
    global LAST_BACKUP
    while True:
        try:
            ensure_core_node();RETURNS.tick();MICRO.tick();STATE["activity_context"]=VERIFIER.status();await auto_desktop_attention();await maybe_autogoal();await maybe_web_brain();STATE["maintenance"]=await asyncio.to_thread(MAINT.safe_tick,HUB.devices(),AI.health());await MAINT.propose_if_needed(health())
            now=time.time();interval=float(CFG.get("backup_interval_minutes",30))*60
            if now-LAST_BACKUP>=interval:
                await asyncio.to_thread(STORAGE.backup,DATA/"backups",CFG.get("backup_keep",14));LAST_BACKUP=now
        except Exception as e:
            STATE["last_error"]=f"{type(e).__name__}: {e}"
        await asyncio.sleep(max(2,int(CFG.get("verdict_interval_seconds",5))))

async def auto_desktop_attention():
    if not CURRENT["session_id"]:return
    sample=await asyncio.to_thread(DESKTOP.sample)
    _,gaze=HUB.primary_gaze()
    fused=FUSION.score(gaze,sample)
    STATE["active_window"]=sample.get("active_window","")
    STATE["active_process"]=sample.get("process","")
    STATE["screen_change"]=sample.get("screen_change")
    STATE["input_recent"]=sample.get("input_recent")
    STATE["sensor_confidence"]=fused.get("confidence")
    await asyncio.to_thread(attention,AttentionReq(score=fused["score"],screen_change=sample.get("screen_change"),input_recent=sample.get("input_recent")))

async def maybe_web_brain():
    if not WEB.running:await WEB.run_once(force=False)

def policy_actions(kind="study"):
    context={"risk":STATE.get("risk",{}).get("level"),"phase":STATE.get("phase"),"kind":kind,
             "attention":STATE.get("attention"),"flow":bool(STATE.get("flow"))}
    return POLICIES.effective(context,"study")

def operating_mode():
    devices=HUB.devices()
    online=[d for d in devices if not d.get("stale") and d.get("status","active")!="retired"]
    laptop=any(d.get("kind") in ("laptop","desktop","windows","server","core") and (d.get("capabilities") or {}).get("core") for d in online)
    mobile=any(d.get("kind") in ("android","phone","tablet") for d in online)
    configured_ai=any(bool(v) for v in AI.health().get("models",{}).values())
    if laptop and configured_ai:return {"level":"FULL","description":"laptop compute + configured AI + replicated spine"}
    if mobile and configured_ai:return {"level":"ONLINE_MOBILE","description":"mobile node + configured online/local route"}
    if mobile:return {"level":"SURVIVAL","description":"mobile guard, cached state and return contracts"}
    return {"level":"CORE_ONLY","description":"core state available; no fresh device heartbeat"}

async def maybe_autogoal():
    global LAST_AUTOGOAL
    if not CURRENT["session_id"] or MICRO.current:return
    activity=VERIFIER.status()
    if activity and activity.get("blocks_study"):return
    now=time.time();gaze_device,gaze=HUB.primary_gaze();gaze=gaze or {"zone":"laptop","quality":0.0,"event":""}
    high_value=(gaze.get("event") or "").lower() in {"long_fixation","rapid_revisit","flighty","stuck"} or STATE.get("risk",{}).get("level")=="high"
    interval=8 if high_value else int(CFG.get("screen_vision_interval_seconds",20))
    if now-LAST_AUTOGOAL<interval:return
    LAST_AUTOGOAL=now
    result=await QUESTIONS.from_gaze(gaze,deep=high_value)
    if result.get("ok"):
        d=result["data"];actions=policy_actions(d.get("kind","study"))
        forced=actions.get("intervention.style") or actions.get("novelty.style")
        allowed={"duel","mystery","boss","precision","sprint","teachback","streak","comeback"}
        style=forced if forced in allowed else ENG.choose_style(d.get("kind","study"))
        secs=d.get("seconds",60)
        if isinstance(actions.get("microgoal.seconds"),(int,float)):secs=max(20,min(180,int(actions["microgoal.seconds"])))
        w=ENG.wrap(d.get("instruction") or d.get("question") or "همین بخش",style,secs,MICRO.streak,d.get("hook",""))
        g=MICRO.start(CURRENT["session_id"],d.get("instruction") or d.get("question") or "همین بخش",d.get("kind","study"),d.get("question",""),
                      d.get("expected",""),"gaze-ai" if high_value else "context-ai",secs,style,w["display_instruction"],w["salience"],d.get("topic",""))
    else:
        style=ENG.choose_style("recall")
        instruction="کوچک‌ترین بخش بعدی جلویت را بخوان؛ بعد بدون نگاه در یک جمله توضیحش بده."
        w=ENG.wrap(instruction,style,45,MICRO.streak)
        g=MICRO.start(CURRENT["session_id"],instruction,"recall","در یک جمله چه فهمیدی؟","","local-fallback",45,style,w["display_instruction"],w["salience"],"")
    SPINE.set("microgoal",g,"core");BUS.queue("microgoal",g,ttl_seconds=900)

@app.get("/")
def root_ui():return FileResponse(BASE/"app"/"static"/"index.html")

@app.get("/api/state")
def state():
    STATE["devices"]=HUB.devices();STATE["activity_context"]=VERIFIER.status();STATE["theme"]=ENG.daily_theme;STATE["microgoal"]=MICRO.public();STATE["return_contract"]=RETURNS.active();STATE["session"]=CURRENT
    rival=RIVAL.ensure_round(CURRENT["session_id"]) if CURRENT["session_id"] else None
    STATE["rival"]=rival
    STATE["future"]=FUTURE.forecast(float(STATE.get("attention_score",50)),STATE.get("gaze"),MICRO.public(),STATE.get("risk"),bool(STATE.get("flow")),rival)
    STATE["operating_mode"]=operating_mode();STATE["effective_policies"]=policy_actions(MICRO.public().get("kind","study") if MICRO.public() else "study")
    return STATE

@app.get("/api/health")
def health():
    return {"ok":STORAGE.integrity().get("ok",False),"database":STORAGE.integrity(),"ai":AI.health(),"screen_error":SCREEN.last_error,
            "devices":HUB.devices(),"web_brain":{"last_run":WEB.last_run,"last_error":WEB.last_error},
            "protocol_version":CFG.get("protocol_version",3),"operating_mode":operating_mode()}

@app.post("/api/session/start")
def start_session(r:StartReq):
    if CURRENT["session_id"]:return {"ok":True,"session":CURRENT,"reason":"already-active"}
    now=int(time.time());c=db();cur=c.execute("insert into sessions(started_at,goal,plan) values(?,?,?)",(now,r.goal,r.plan));c.commit();sid=int(cur.lastrowid);c.close()
    CURRENT.update({"session_id":sid,"goal":r.goal,"plan":r.plan,"started_at":now});FOCUS.session_started=time.time();RIVAL.ensure_round(sid)
    SPINE.set("session",dict(CURRENT),"core")
    return {"ok":True,"session":CURRENT}

@app.post("/api/session/stop")
def stop_session():
    sid=CURRENT["session_id"];summary=MEM.session_summary(sid) if sid else {"text":"","points":[]}
    if sid:
        c=db();c.execute("update sessions set ended_at=?,summary=? where id=?",(int(time.time()),summary["text"],sid));c.commit();c.close()
    CURRENT.update({"session_id":None,"goal":"","plan":"","started_at":None});MICRO.current=None
    SPINE.set("session",dict(CURRENT),"core");SPINE.set("microgoal",None,"core")
    BUS.queue("clear_microgoal",{},ttl_seconds=300)
    return {"ok":True,"summary":summary,"later_inbox":FIREWALL.pending(20)}

@app.post("/api/micro/start")
def micro_start(r:MicroReq):
    if not CURRENT["session_id"]:return {"ok":False,"reason":"start-session-first"}
    actions=policy_actions(r.kind);forced=actions.get("intervention.style") or actions.get("novelty.style")
    allowed={"duel","mystery","boss","precision","sprint","teachback","streak","comeback"}
    style=forced if forced in allowed else ENG.choose_style(r.kind)
    secs=r.seconds or actions.get("microgoal.seconds") or CFG.get("microgoal_default_seconds",60)
    secs=max(20,min(180,int(secs)));w=ENG.wrap(r.instruction,style,secs,MICRO.streak,r.hook)
    g=MICRO.start(CURRENT["session_id"],r.instruction,r.kind,r.question,r.expected,"manual",secs,style,w["display_instruction"],w["salience"],r.context_ref)
    SPINE.set("microgoal",g,"core");BUS.queue("microgoal",g,ttl_seconds=900);return {"ok":True,"microgoal":g,"theme":w["theme"]}

@app.post("/api/micro/feedback")
async def micro_feedback(r:FeedbackReq):
    before=float(STATE.get("attention_score",50))
    result=MICRO.feedback(r.answer,r.status,r.note,r.confidence,r.latency_ms,r.topic,r.error_type)
    if not result.get("ok"):return result

    finished=result.get("finished",{})
    source=finished.get("source","")
    raw_topic=(r.topic or finished.get("context_ref") or "").strip()
    topic=raw_topic[7:] if raw_topic.startswith("repair:") else raw_topic
    result["consequence"]=ENG.feedback(result["passed"],result.get("style",""),result.get("streak",0))
    ENG.record_trial(result.get("style","") or "precision",result["passed"],before,float(STATE.get("attention_score",before)),r.latency_ms)
    BUS.queue("feedback",{"text":result["consequence"],"passed":result["passed"],"clear_microgoal":True},ttl_seconds=180)
    SPINE.set("microgoal",None,"core")

    if topic:
        result["learning_model"]=LEARN.observe(topic,result["passed"],r.error_type)

    actions=policy_actions(finished.get("kind","study"))
    if CURRENT["session_id"] and source!="repair" and actions.get("competition.enabled",True):
        RIVAL.add_user_score(CURRENT["session_id"],3 if result["passed"] else -1)

    # Failure becomes repair -> retest, rather than silent abandonment.
    if not result["passed"] and source!="repair" and CURRENT["session_id"]:
        repair=await QUESTIONS.repair_after_failure(finished,r.answer,r.error_type,topic)
        if repair.get("ok"):
            d=repair["data"]
            pending={"instruction":d.get("retest_instruction") or finished.get("instruction",""),
                     "question":d.get("retest_question") or finished.get("question",""),
                     "expected":d.get("retest_expected",""),"seconds":d.get("retest_seconds",55),
                     "topic":d.get("topic") or topic,"error_type":d.get("error_type") or r.error_type}
            SPINE.set("pending_retest",pending,"core")
            instruction=d.get("repair_instruction") or "علت اشتباه را در یک جمله مشخص کن."
            question=d.get("repair_question") or "اشتباه دقیقاً از کجا شروع شد؟"
            secs=d.get("repair_seconds",35)
        else:
            pending={"instruction":finished.get("instruction",""),"question":finished.get("question",""),
                     "expected":finished.get("expected",""),"seconds":55,"topic":topic,"error_type":r.error_type}
            SPINE.set("pending_retest",pending,"core")
            instruction="در یک جمله مشخص کن اشتباهت مفهومی بود، بی‌دقتی بود، عجله بود یا محاسبات."
            question="علت خطا چه بود و دفعه بعد دقیقاً چه چیزی را چک می‌کنی؟";secs=35
        style="comeback";w=ENG.wrap(instruction,style,secs,MICRO.streak)
        g=MICRO.start(CURRENT["session_id"],instruction,"repair",question,"","repair",secs,style,
                      w["display_instruction"],w["salience"],"repair:"+topic)
        SPINE.set("microgoal",g,"core");BUS.queue("microgoal",g,ttl_seconds=900)
        result["repair_microgoal"]=g

    elif result["passed"] and source=="repair" and CURRENT["session_id"]:
        pending=SPINE.get("pending_retest")
        if pending and pending.get("value"):
            d=pending["value"];secs=max(20,min(120,int(d.get("seconds") or 55)))
            instruction=d.get("instruction") or "همان مفهوم را دوباره حل کن."
            style="precision";w=ENG.wrap(instruction,style,secs,MICRO.streak)
            g=MICRO.start(CURRENT["session_id"],instruction,"retest",d.get("question",""),d.get("expected",""),
                          "retest",secs,style,w["display_instruction"],w["salience"],d.get("topic",""))
            SPINE.set("pending_retest",None,"core");SPINE.set("microgoal",g,"core")
            BUS.queue("microgoal",g,ttl_seconds=900);result["retest_microgoal"]=g
    elif source=="retest":
        SPINE.set("pending_retest",None,"core")

    return result

@app.post("/api/return/start")
def return_start(r:ReturnReq):
    try:return {"ok":True,"contract":RETURNS.create(r.text,r.minutes,r.due_at)}
    except Exception as e:return {"ok":False,"reason":str(e)}

@app.post("/api/return/ack")
def return_ack(r:AckReq):return RETURNS.acknowledge(r.contract_id)

@app.post("/api/device/heartbeat")
def heartbeat(r:DeviceReq):return HUB.heartbeat(r.device_id,r.kind,r.name,r.capabilities,r.state,r.hardware_fingerprint)

@app.get("/api/devices")
def devices():return {"items":HUB.devices(include_retired=True),"capabilities":HUB.capability_report()}

@app.post("/api/devices/replace")
def replace_device(r:DeviceReplaceReq):
    return HUB.replace(r.old_device_id,r.new_device_id,r.kind,r.name,r.capabilities,r.hardware_fingerprint)

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
    phase=FOCUS.phase(score);intervention="";kind="";activity=VERIFIER.status()
    if activity and activity.get("activity")=="driving" and activity.get("confidence",0)>=.35:
        STATE.update({"attention_score":score,"phase":"DRIVING","last_intervention":"","activity_context":activity})
        return STATE
    critical=score<28 or float((gaze or {}).get("away_streak_seconds") or 0)>=8
    if not flow and FOCUS.can_intervene(critical):
        if critical:intervention="ایلا: RETURN. فقط همین مأموریت.";kind="critical-return"
        elif risk["level"]=="high":intervention="ایلا: افت نزدیکه؛ انتخاب اضافه نداریم. همین micro-goal را تحویل بده.";kind="prefailure"
        if intervention:
            FOCUS.mark_intervention();BUS.queue("speak" if critical else "notify",{"text":intervention},ttl_seconds=120)
            c=db();c.execute("insert into interventions(ts,session_id,kind,pre_score,metadata) values(?,?,?,?,?)",(int(time.time()),CURRENT["session_id"],kind,score,json.dumps({"risk":risk},ensure_ascii=False)));c.commit();c.close()
    now=int(time.time());c=db()
    pending=c.execute("select id,pre_score from interventions where post_score is null and ts<=? and ts>=?",(now-25,now-180)).fetchall()
    for p in pending:
        pre=float(p["pre_score"] or 0);c.execute("update interventions set post_score=?,outcome=? where id=?",(score,score-pre,p["id"]))
    c.commit();c.close()
    rival=RIVAL.ensure_round(CURRENT["session_id"]) if CURRENT["session_id"] else None
    future=FUTURE.forecast(score,gaze,MICRO.public(),risk,flow,rival)
    STATE.update({"attention_score":score,"attention":"study" if score>=60 else ("uncertain" if score>=45 else "off-task"),"risk":risk,"flow":flow,"phase":phase,"learning_pulse":pulse,"integrity":integrity,"last_intervention":intervention,"future":future})
    if CURRENT["session_id"]:
        c=db();c.execute("""insert into attention_samples(ts,session_id,device_id,score,zone,study_ratio,away_streak,fixation,jump_rate,risk,metadata)
          values(?,?,?,?,?,?,?,?,?,?,?)""",(now,CURRENT["session_id"],STATE.get("gaze_device") or "",score,(gaze or {}).get("zone",""),(gaze or {}).get("study_ratio_15"),(gaze or {}).get("away_streak_seconds"),(gaze or {}).get("max_fixation_seconds"),(gaze or {}).get("jump_rate"),risk["level"],json.dumps(integrity,ensure_ascii=False)));c.commit();c.close()
    return STATE

@app.post("/api/context/current")
def set_context(r:ContextReq):return {"ok":True,"id":CONTEXT.set(r.kind,r.title,r.content,r.ref)}

@app.post("/api/context/image")
def set_context_image(r:ImageContextReq):
    raw=r.data_url.split(",",1)[-1]
    try:data=base64.b64decode(raw,validate=True)
    except Exception:return {"ok":False,"reason":"bad-base64"}
    if len(data)>8_000_000:return {"ok":False,"reason":"image-too-large"}
    path=DATA/"current_page.jpg";path.write_bytes(data)
    return {"ok":True,"id":CONTEXT.set("image",r.title,"",str(path)),"bytes":len(data)}

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

@app.get("/api/spine")
def spine_state():return {"state":SPINE.snapshot(),"conflicts":SPINE.conflicts()}

@app.post("/api/spine/{key}")
def spine_set(key:str,r:SpineSetReq):return SPINE.set(key,r.value,r.source_device,r.expected_revision)

@app.get("/api/spine/conflicts/open")
def spine_conflicts():return {"items":SPINE.conflicts()}

@app.post("/api/spine/conflicts/{conflict_id}/resolve")
def spine_conflict_resolve(conflict_id:int,r:ConflictResolveReq):
    return SPINE.resolve_conflict(conflict_id,r.choice,"user")

@app.get("/api/policies")
def policies():return {"items":POLICIES.list(False)}

@app.post("/api/policies")
def add_policy(r:PolicyReq):return POLICIES.add(r.scope,r.trigger,r.action,r.priority,"user",r.rationale)

@app.post("/api/policies/{policy_id}/disable")
def disable_policy(policy_id:str):return POLICIES.disable(policy_id,"user")

@app.get("/api/policies/{policy_id}/history")
def policy_history(policy_id:str):return {"items":POLICIES.history(policy_id)}

@app.post("/api/policies/{policy_id}/rollback")
def policy_rollback(policy_id:str,r:PolicyRollbackReq):return POLICIES.rollback(policy_id,r.version,"user")

@app.get("/api/capabilities")
def capability_self_description():
    return {"identity":SPINE.get("identity"),"architecture":SPINE.get("architecture"),
            "devices":HUB.devices(include_retired=True),"device_capabilities":HUB.capability_report(),
            "ai":AI.health(),"operating_mode":operating_mode(),
            "core_features":["microgoal-wait-verify","return-contract","gaze-fusion","screen-context",
                             "live-evolution","policy-rollback","student-model","error-genome",
                             "event-sync","spine-conflict-preservation","device-replacement","self-maintenance"],
            "capability_requests":EVOLVE.capability_requests(20)}

@app.post("/api/evolve")
async def evolve(r:EvolveReq):return await EVOLVE.apply_request(r.text)

@app.get("/api/learning/model")
def learning_model():return {"student":LEARN.student(),"errors":LEARN.errors(),"behavior":LEARN.behavior(),"due_reviews":LEARN.due_reviews()}

@app.get("/api/later")
def later():return {"items":FIREWALL.pending()}
@app.post("/api/later/{item_id}/done")
def later_done(item_id:int):FIREWALL.clear(item_id);return {"ok":True}

@app.get("/api/research/latest")
def research_latest():return {"items":WEB.latest()}
@app.post("/api/research/run")
async def research_run():return await WEB.run_once(force=True)

@app.post("/api/rival/score")
def rival_score(r:ScoreReq):
    if not CURRENT["session_id"]:return {"ok":False,"reason":"no-session"}
    return {"ok":True,"state":RIVAL.add_user_score(CURRENT["session_id"],r.delta)}

@app.get("/api/sync/snapshot")
def sync_snapshot():
    rival=RIVAL.state(CURRENT["session_id"]) if CURRENT["session_id"] else None
    return SYNC.snapshot(CURRENT,MICRO.public(),RETURNS.active(),rival,WEB.latest(10),POLICIES.list(False),HUB.devices(include_retired=True))

@app.get("/api/sync/events")
def sync_events(after_seq:int=0,limit:int=200):return SYNC.pull_events(after_seq,limit)

@app.post("/api/sync/event")
def sync_event(r:EventReq):return EVENTS.ingest(r.event)

@app.post("/api/sync/offer")
def sync_offer(r:SnapshotReq):return SYNC.store_offer(r.device_id,r.snapshot)

@app.post("/api/sync/restore-memory/{device_id}")
def sync_restore(device_id:str):return SYNC.restore_memory_if_empty(device_id)

@app.post("/api/sync/restore-spine/{device_id}")
def sync_restore_spine(device_id:str):return SYNC.restore_spine_from_device(device_id)

@app.post("/api/activity/claim")
def activity_claim(r:ActivityClaimReq):
    out=VERIFIER.claim(r.activity,r.minutes,r.note)
    STATE["activity_context"]=out
    if out.get("activity")=="driving":
        BUS.queue("clear_microgoal",{},ttl_seconds=300)
    return out

@app.post("/api/activity/evidence")
def activity_evidence(r:ActivityEvidenceReq):
    out=VERIFIER.evidence(r.device_id,r.facts,r.kind);STATE["activity_context"]=VERIFIER.status();return out

@app.get("/api/activity/status")
def activity_status():return VERIFIER.status() or {"active":False}

@app.post("/api/activity/finish")
def activity_finish():STATE["activity_context"]=None;return VERIFIER.finish()

@app.post("/api/stimulus/ball")
def ball_stimulus(r:BallStimulusReq):
    c=db();c.execute("insert into stimulus_events(ts,source,event,payload) values(?,?,?,?)",
      (int(r.ts/1000) if r.ts and r.ts>10_000_000_000 else int(r.ts or time.time()),r.source,r.event,json.dumps(r.extra,ensure_ascii=False)));c.commit();c.close()
    return {"ok":True}

@app.get("/api/maintenance/status")
def maintenance_status():return MAINT.status()

@app.post("/api/maintenance/audit")
async def maintenance_audit():
    report=MAINT.safe_tick(HUB.devices(),AI.health());proposal=await MAINT.propose_if_needed(health());return {"report":report,"proposal":proposal}

@app.post("/api/chat")
async def chat(r:ChatReq):
    msg=r.message.strip()
    if any(x in msg for x in ("از این به بعد","از حالا به بعد","از امروز به بعد")):
        evolved=await EVOLVE.apply_request(msg)
        if evolved.get("ok") and evolved.get("kind")=="policy":
            return {"text":"این تغییر رفتاری ثبت و version شد. اگر نتیجه‌اش بد باشد می‌توانیم غیرفعالش کنیم یا برگردانیم.","action":"live-evolution","result":evolved}
        if evolved.get("ok") and evolved.get("kind")=="capability":
            return {"text":"این درخواست به قابلیت جدید نیاز دارد؛ به‌عنوان capability request ثبتش کردم تا در مسیر ایزوله ساخته و تست شود.","action":"capability-request","result":evolved}
    activity=VERIFIER.parse_claim(msg)
    if activity:
        out=VERIFIER.claim(activity,note=msg)
        STATE["activity_context"]=out
        if activity=="driving":
            BUS.queue("clear_microgoal",{},ttl_seconds=300)
            return {"text":"رانندگی را ثبت کردم. تا وقتی احتمال رانندگی وجود دارد مأموریت بصری و فشار مطالعاتی نمی‌دهم؛ راستی‌آزمایی فقط با سنسورهای passive انجام می‌شود.","action":"activity-claim","activity":out}
        if activity=="sleeping":
            return {"text":"خواب را ثبت کردم. ایلا مزاحمت مطالعاتی را متوقف می‌کند و فقط با شواهد passive وضعیت را می‌سنجد.","action":"activity-claim","activity":out}
        if activity=="eating":
            return {"text":"زمان غذا ثبت شد. خوردن غذا از روی گوشی به‌طور قابل‌اعتماد قابل اثبات نیست؛ اگر لازم باشد فقط با شواهد اختیاری و غیرمداوم بررسی می‌کنم.","action":"activity-claim","activity":out}
    local=INTENTS.local(msg)
    if local["intent"]=="return_contract":
        c=RETURNS.create(msg,minutes=local["minutes"])
        return {"text":f"باشه. {local['minutes']:g} دقیقه ثبت شد؛ اگر برنگردی خودم پیگیری می‌کنم.","action":"return_contract","contract":c}
    if local["intent"]=="return_ack":
        a=RETURNS.acknowledge()
        return {"text":"برگشتی. همان رشته قبلی را ادامه می‌دهیم.","action":"return_ack","result":a}
    if CURRENT["session_id"] and MICRO.public():
        cls=await INTENTS.classify_focus(AI,msg,CURRENT["goal"],MICRO.public())
        if cls.get("label")=="unrelated" and cls.get("confidence",0)>=.65:
            item=FIREWALL.defer(msg,"focus-mode")
            return {"text":"این را برای بعد نگه داشتم. الان همان مأموریت فعال را تحویل بده.","action":"deferred","later_id":item}
    context={"goal":CURRENT["goal"],"plan":CURRENT["plan"],"microgoal":MICRO.public(),"return_contract":RETURNS.active(),"theme":ENG.daily_theme,
             "state":STATE,"memory":MEM.relevant(15),"recent_research":WEB.latest(5)}
    txt=await AI.ask("fast",[{"role":"system","content":EILA_SYSTEM},{"role":"user","content":json.dumps(context,ensure_ascii=False)+"\nپیام کاربر: "+msg}],max_tokens=700)
    if txt.startswith("__AI_ERROR__"):txt="مغز زبانی در دسترس نیست؛ قراردادها، micro-goal، حافظه و نگهبانی پایه ادامه دارند."
    return {"text":txt}

@app.post("/api/backup")
def backup():return {"ok":True,"path":STORAGE.backup(DATA/"backups",CFG.get("backup_keep",14))}
