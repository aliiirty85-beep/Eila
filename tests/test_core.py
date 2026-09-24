from pathlib import Path
from tempfile import TemporaryDirectory
import time
from app.storage import Storage
from app.command_bus import CommandBus
from app.device_hub import DeviceHub
from app.microgoals import MicroGoalEngine
from app.return_contracts import ReturnContractManager
from app.engagement import EngagementEngine
from app.focus_engine import FocusEngine
from app.learning import LearningPulse
from app.integrity import StudyIntegrity

def env():
    td=TemporaryDirectory();s=Storage(Path(td.name)/"eila.db");s.init();return td,s,CommandBus(s.connect)

def test_storage_integrity():
    td,s,_=env()
    try:assert s.integrity()["ok"]
    finally:td.cleanup()

def test_microgoal_roundtrip():
    td,s,_=env()
    try:
        m=MicroGoalEngine(s.connect,60);g=m.start(1,"سؤال ۱ را حل کن",kind="test",expected="2")
        assert g["remaining_seconds"]>0
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
