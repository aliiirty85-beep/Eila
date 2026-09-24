from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3,time
from app.storage import Storage
from app.command_bus import CommandBus
from app.device_hub import DeviceHub
from app.microgoals import MicroGoalEngine
from app.return_contracts import ReturnContractManager
from app.engagement import EngagementEngine
from app.focus_engine import FocusEngine
from app.learning import LearningPulse
from app.integrity import StudyIntegrity
from app.intent_router import IntentRouter
from app.firewall import StudyFirewall
from app.future_engine import FutureEngine
from app.memory import MemoryManager
from app.sync import SyncManager

def env():
    td=TemporaryDirectory();s=Storage(Path(td.name)/"eila.db");s.init();return td,s,CommandBus(s.connect)

def test_storage_integrity():
    td,s,_=env()
    try:assert s.integrity()["ok"]
    finally:td.cleanup()

def test_migration_adds_columns():
    td=TemporaryDirectory()
    try:
        p=Path(td.name)/"old.db";c=sqlite3.connect(p);c.execute("create table sessions(id integer primary key,started_at integer not null,ended_at integer,goal text,plan text)");c.execute("create table microgoals(id integer primary key,session_id integer,created_at integer not null,deadline_at integer not null,kind text,instruction text,question text,expected text,source text,status text,result_note text)");c.commit();c.close()
        s=Storage(p);s.init();c=s.connect();cols={r["name"] for r in c.execute("pragma table_info(microgoals)")};c.close();assert {"answer","context_ref","engagement_style","display_instruction","salience"}<=cols
    finally:td.cleanup()

def test_microgoal_roundtrip():
    td,s,_=env()
    try:
        m=MicroGoalEngine(s.connect,60);g=m.start(1,"سؤال ۱ را حل کن",kind="test",expected="2");assert g["remaining_seconds"]>0
        out=m.feedback("2",confidence=.8);assert out["ok"] and out["passed"] and out["streak"]==1
    finally:td.cleanup()

def test_return_escalation_and_commands():
    td,s,bus=env()
    try:
        r=ReturnContractManager(s.connect,bus,{"return_escalation_seconds":[0,1,2,3]});c=r.create("ناهار",due_at=int(time.time())-2);actions=r.tick()
        assert actions and actions[0]["contract_id"]==c["id"];assert bus.pending("phone")
    finally:td.cleanup()

def test_device_hub_primary_prefers_quality():
    td,s,_=env()
    try:
        h=DeviceHub(s.connect,15);h.heartbeat("phone");h.heartbeat("tablet");h.ingest_gaze("phone",{"quality":.4,"zone":"laptop"});h.ingest_gaze("tablet",{"quality":.9,"zone":"book"})
        did,g=h.primary_gaze();assert did=="tablet" and g["zone"]=="book"
    finally:td.cleanup()

def test_engagement_avoids_recent_repeat():
    td,s,_=env()
    try:
        e=EngagementEngine(s.connect);a=e.choose_style("test");b=e.choose_style("test");assert a!=b
    finally:td.cleanup()

def test_focus_flow_and_risk():
    f=FocusEngine({"flow_protection_min_attention":78,"intervention_budget_per_5min":4});f.session_started=time.time()-600;m={"remaining_seconds":50};g={"study_ratio_15":.9,"away_streak_seconds":0,"jump_rate":.1}
    f.observe(85);assert f.flow_protected(85,g,m);assert f.phase(85)=="FLOW"

def test_learning_pulse_and_integrity():
    td,s,_=env()
    try:
        c=s.connect();now=int(time.time())
        for p in (1,1,0):c.execute("insert into learning_evidence(ts,kind,passed,confidence) values(?,?,?,?)",(now,"test",p,.8))
        c.commit();c.close();pulse=LearningPulse(s.connect).score(70);assert pulse["attempts"]==3
        integ=StudyIntegrity().assess(30,{"jump_rate":.6},.5,True,pulse);assert integ["suspicion"]>0
    finally:td.cleanup()

def test_return_intent_farsi_digits():
    x=IntentRouter().local("می‌رم ناهار، ۵ دقیقه دیگه برمی‌گردم");assert x["intent"]=="return_contract" and x["minutes"]==5

def test_firewall_defer():
    td,s,_=env()
    try:
        f=StudyFirewall(s.connect);i=f.defer("بعداً درباره فیلم حرف بزنیم");assert i>0 and f.pending()
    finally:td.cleanup()

def test_future_engine():
    out=FutureEngine().forecast(85,{"away_streak_seconds":0},{"remaining_seconds":30},{"level":"low"},True,None);assert "سکوت" in out["now_5s"]

def test_phone_snapshot_memory_restore():
    td,s,_=env()
    try:
        m=MemoryManager(s.connect);sync=SyncManager(s.connect,m,2);snap={"protocol_version":2,"memory":[{"category":"behavior","key":"x","value":"y","confidence":.8}]}
        sync.store_offer("phone",snap);r=sync.restore_memory_if_empty("phone");assert r["ok"] and m.relevant()
    finally:td.cleanup()


def test_activity_verifier_driving_is_safety_first():
    from app.context_verifier import ContextVerifier
    td,s,_=env()
    try:
        v=ContextVerifier(s.connect,{"activity_claim_defaults_minutes":{"driving":60}})
        claim=v.claim("driving",minutes=10)
        assert claim["activity"]=="driving"
        assert claim["safety_mode"]=="driving"
        verified=v.evidence("phone",{"activity":"in_vehicle","speed_mps":12},"test")
        assert verified["verdict"]=="probable"
        assert verified["confidence"]>=.8
    finally:td.cleanup()

def test_eating_is_not_falsely_verified_from_weak_phone_signals():
    from app.context_verifier import ContextVerifier
    td,s,_=env()
    try:
        v=ContextVerifier(s.connect,{"activity_claim_defaults_minutes":{"eating":30}})
        v.claim("eating",minutes=10)
        out=v.evidence("phone",{"screen_interactive":False,"charging":False},"test")
        assert out["verdict"]=="uncertain"
        assert out["confidence"]<.65
    finally:td.cleanup()

def test_maintenance_safe_tick_creates_backup():
    from app.maintenance import MaintenanceEngine
    class DummyAI:
        def health(self):return {"models":{}}
    td,s,_=env()
    try:
        m=MaintenanceEngine(s.connect,s,DummyAI(),Path(td.name),{"maintenance_interval_minutes":0,"backup_keep":2})
        out=m.safe_tick([],{"models":{}})
        assert out["database"]["ok"]
        assert list((Path(td.name)/"backups").glob("eila-*.db"))
    finally:td.cleanup()
