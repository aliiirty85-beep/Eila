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


def test_event_bus_is_idempotent():
    from app.sync import EventBus
    td,s,_=env()
    try:
        e=EventBus(s.connect)
        one=e.emit("test.event",{"x":1},event_id="same-id")
        two=e.ingest({"event_id":"same-id","kind":"test.event","payload":{"x":99},"source_device":"phone"})
        assert one["event_id"]=="same-id"
        assert two["ok"] and two["duplicate"]
        assert len(e.list_since(0,20))==1
    finally:td.cleanup()

def test_spine_revision_conflict_and_snapshot():
    from app.sync import EventBus,SpineState
    td,s,_=env()
    try:
        e=EventBus(s.connect);sp=SpineState(s.connect,e)
        a=sp.set("identity",{"name":"Eila"},"phone",expected_revision=0)
        assert a["ok"] and a["revision"]==1
        conflict=sp.set("identity",{"name":"Other"},"laptop",expected_revision=0)
        assert not conflict["ok"] and conflict["reason"]=="revision-conflict"
        assert sp.snapshot()["identity"]["value"]["name"]=="Eila"
    finally:td.cleanup()

def test_device_replacement_preserves_identity_but_requests_recalibration():
    from app.sync import EventBus
    from app.device_hub import DeviceHub
    td,s,_=env()
    try:
        hub=DeviceHub(s.connect,15,EventBus(s.connect))
        hub.heartbeat("old-laptop","laptop","Old",{"screen":True},{},hardware_fingerprint="old-hw")
        out=hub.replace("old-laptop","new-laptop","laptop","New",{"screen":True},"new-hw")
        assert out["ok"]
        assert "gaze-screen-geometry" in out["requires_recalibration"]
        assert hub.get("old-laptop")["status"]=="retired"
        assert hub.get("new-laptop")["status"]=="active"
    finally:td.cleanup()

def test_live_policy_is_versioned_and_safe():
    from app.sync import EventBus
    from app.memory import PolicyEngine
    td,s,_=env()
    try:
        p=PolicyEngine(s.connect,EventBus(s.connect))
        ok=p.add("study",{"risk":"high"},{"intervention.style":"duel"},70)
        assert ok["ok"] and ok["policy"]["version"]==1
        bad=p.add("global",{},{"filesystem.delete":"all"},99)
        assert not bad["ok"]
        assert p.resolve({"risk":"high"},"study")
    finally:td.cleanup()

def test_learning_model_schedules_fast_repair_after_error():
    from app.learning import LearningModel
    td,s,_=env()
    try:
        m=LearningModel(s.connect)
        now=1_700_000_000
        out=m.observe("زیست/تنفس",False,"concept-gap",now=now)
        assert out["repair_due"]==now+15*60
        due=m.due_reviews(now+15*60)
        assert due and due[0]["reason"]=="repair-retest"
        assert m.errors()[0]["error_type"]=="concept-gap"
    finally:td.cleanup()

def test_sync_offer_rejects_wrong_protocol_and_deduplicates_events():
    from app.sync import SyncManager,EventBus,SpineState
    td,s,_=env()
    try:
        mem=MemoryManager(s.connect);events=EventBus(s.connect);sp=SpineState(s.connect,events)
        sync=SyncManager(s.connect,mem,3,events,sp)
        bad=sync.store_offer("phone",{"protocol_version":2})
        assert not bad["ok"] and bad["reason"]=="protocol-mismatch"
        event={"event_id":"abc","kind":"device.test","payload":{"ok":True},"source_device":"phone"}
        snap={"protocol_version":3,"events_tail":[event,event]}
        good=sync.store_offer("phone",snap)
        assert good["ok"] and good["events_applied"]==1 and good["duplicates"]==1
    finally:td.cleanup()


def test_policy_history_and_rollback():
    from app.sync import EventBus
    from app.memory import PolicyEngine
    td,s,_=env()
    try:
        p=PolicyEngine(s.connect,EventBus(s.connect))
        a=p.add("study",{},{"microgoal.seconds":45},60)
        pid=a["policy"]["policy_id"]
        b=p.add("study",{},{"microgoal.seconds":70},60,policy_id=pid)
        assert b["policy"]["version"]==2
        hist=p.history(pid)
        assert [x["version"] for x in hist][:2]==[2,1]
        r=p.rollback(pid,1)
        assert r["ok"] and r["policy"]["action"]["microgoal.seconds"]==45
        assert r["policy"]["version"]==3
    finally:td.cleanup()

def test_replica_offer_restores_missing_spine_state():
    from app.sync import EventBus,SpineState,SyncManager
    td,s,_=env()
    try:
        mem=MemoryManager(s.connect);events=EventBus(s.connect);sp=SpineState(s.connect,events)
        sync=SyncManager(s.connect,mem,3,events,sp)
        snap={"protocol_version":3,"spine":{
            "session":{"revision":4,"updated_at":1700000000,"source_device":"phone",
                       "value":{"goal":"زیست","session_id":12}}
        },"events_tail":[],"policies":[]}
        out=sync.store_offer("phone",snap)
        assert out["ok"] and out["spine_applied"]==1
        assert sp.get("session")["value"]["goal"]=="زیست"
    finally:td.cleanup()

def test_maintenance_synthetic_db_probe():
    from app.maintenance import MaintenanceEngine
    class DummyAI: pass
    td,s,_=env()
    try:
        m=MaintenanceEngine(s.connect,s,DummyAI(),Path(td.name),{"maintenance_interval_minutes":0,"backup_keep":1})
        checks=m.synthetic_checks()
        assert checks["db_read_write"]["ok"]
    finally:td.cleanup()


def test_heartbeat_does_not_bump_revision_or_emit_event_when_only_state_changes():
    from app.sync import EventBus
    td,s,_=env()
    try:
        events=EventBus(s.connect);hub=DeviceHub(s.connect,15,events)
        a=hub.heartbeat("phone","phone","P",{"gaze":True},{"battery":90},"fp1")
        b=hub.heartbeat("phone","phone","P",{"gaze":True},{"battery":89},"fp1")
        assert a["device_revision"]==b["device_revision"]==1
        rows=events.list_since(0,20)
        assert len(rows)==1 and rows[0]["kind"]=="device.joined"
        c2=hub.heartbeat("phone","phone","P",{"gaze":True,"tts":True},{"battery":88},"fp1")
        assert c2["device_revision"]==2
        assert events.tail(10)[-1]["kind"]=="device.capabilities.changed"
    finally:td.cleanup()

def test_event_tail_returns_newest_events():
    from app.sync import EventBus
    td,s,_=env()
    try:
        e=EventBus(s.connect)
        for i in range(520):e.emit("x",{"i":i},event_id="e-"+str(i))
        tail=e.tail(500)
        assert len(tail)==500
        assert tail[0]["payload"]["i"]==20
        assert tail[-1]["payload"]["i"]==519
    finally:td.cleanup()

def test_schema_v4_to_v5_creates_spine_tables_and_device_columns():
    td=TemporaryDirectory()
    try:
        p=Path(td.name)/"old.db"
        c=sqlite3.connect(p)
        c.execute("create table meta(key text primary key,value text not null)")
        c.execute("create table devices(device_id text primary key,kind text default 'unknown',name text default '',last_seen integer not null,capabilities text default '{}',state text default '{}')")
        c.execute("create table sessions(id integer primary key autoincrement,started_at integer not null,ended_at integer,goal text default '',plan text default '',summary text default '')")
        c.execute("create table microgoals(id integer primary key autoincrement,session_id integer,created_at integer not null,deadline_at integer not null,kind text not null,instruction text not null,question text default '',expected text default '',source text default 'manual',status text default 'waiting',answer text default '',result_note text default '',engagement_style text default '',display_instruction text default '',salience text default '',context_ref text default '')")
        c.commit();c.close()
        s=Storage(p);s.init();c=s.connect()
        tables={r[0] for r in c.execute("select name from sqlite_master where type='table'").fetchall()}
        cols={r["name"] for r in c.execute("pragma table_info(devices)").fetchall()}
        version=c.execute("select value from meta where key='schema_version'").fetchone()[0]
        c.close()
        assert {"spine_state","events","behavior_policies","behavior_policy_history","student_topics","error_genome"}<=tables
        assert {"status","retired_at","hardware_fingerprint","device_revision"}<=cols
        assert version=="5"
    finally:td.cleanup()
