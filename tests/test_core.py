from pathlib import Path
from tempfile import TemporaryDirectory
import time

from app.storage import Storage
from app.command_bus import CommandBus
from app.microgoals import MicroGoalEngine
from app.return_contracts import ReturnContractManager
from app.engagement import EngagementEngine

def env():
    td=TemporaryDirectory()
    s=Storage(Path(td.name)/"eila.db"); s.init()
    bus=CommandBus(s.connect)
    return td,s,bus

def test_storage_integrity():
    td,s,_=env()
    try:
        assert s.integrity()["ok"]
    finally:
        td.cleanup()

def test_microgoal_roundtrip():
    td,s,_=env()
    try:
        m=MicroGoalEngine(s.connect,60)
        g=m.start(1,"سؤال ۱ را حل کن",kind="test",expected="2")
        assert g["remaining_seconds"]>0
        out=m.feedback("2")
        assert out["ok"] and out["passed"] and out["streak"]==1
    finally:
        td.cleanup()

def test_return_contract_escalation():
    td,s,bus=env()
    try:
        r=ReturnContractManager(s.connect,bus,{"return_escalation_seconds":[0,1,2,3]})
        c=r.create("ناهار",due_at=int(time.time())-2)
        actions=r.tick()
        assert actions and actions[0]["contract_id"]==c["id"]
        assert bus.pending("phone")
    finally:
        td.cleanup()

def test_engagement_avoids_recent_repeat():
    e=EngagementEngine()
    first=e.choose_style("test")
    second=e.choose_style("test")
    assert first!=second
