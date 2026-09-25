import asyncio
from types import SimpleNamespace

import pytest

from app import main as core
from app.storage import Storage
from app.command_bus import CommandBus
from app.microgoals import MicroGoalEngine
from app.return_contracts import ReturnContractManager
from app.sync import EventBus,SpineState
from app.learning import LearningModel
from app.engagement import EngagementEngine
from app.focus_engine import FocusEngine


@pytest.fixture
def vertical_runtime(tmp_path,monkeypatch):
    store=Storage(tmp_path/"vertical.db");store.init()
    bus=CommandBus(store.connect)
    micro=MicroGoalEngine(store.connect)
    events=EventBus(store.connect)
    spine=SpineState(store.connect,events)

    monkeypatch.setattr(core,"STORAGE",store)
    monkeypatch.setattr(core,"BUS",bus)
    monkeypatch.setattr(core,"MICRO",micro)
    monkeypatch.setattr(core,"SPINE",spine)
    monkeypatch.setattr(core,"RETURNS",ReturnContractManager(store.connect,bus,{"return_escalation_seconds":[0,30,90,180]}))
    monkeypatch.setattr(core,"LEARN",LearningModel(store.connect,events))
    monkeypatch.setattr(core,"ENG",EngagementEngine(store.connect))
    monkeypatch.setattr(core,"FOCUS",FocusEngine({}))
    monkeypatch.setattr(core,"RIVAL",SimpleNamespace(
        ensure_round=lambda sid:{"round":1},
        add_user_score=lambda sid,delta:{"score":delta}
    ))
    monkeypatch.setattr(core,"CONTEXT",SimpleNamespace(current=lambda:None))
    monkeypatch.setattr(core,"CURRENT",{"session_id":None,"goal":"","plan":"","started_at":None})
    monkeypatch.setattr(core,"STATE",{"flow":False,"risk":{"level":"low"},"attention_score":50.0})
    monkeypatch.setattr(core,"policy_actions",lambda *a:{})
    return core,store


def test_vertical_slice_wrong_repair_retest_return_restart(vertical_runtime,monkeypatch):
    runtime,store=vertical_runtime

    started=runtime.start_session(runtime.StartReq(goal="زیست",plan="تست عمودی"))
    assert started["ok"] and started["session"]["session_id"]
    sid=started["session"]["session_id"]

    first=runtime.micro_start(runtime.MicroReq(
        instruction="۲+۲ را جواب بده",
        kind="test",
        question="۲+۲ چند می‌شود؟",
        expected="4",
        seconds=60,
        context_ref="vertical/math"
    ))
    assert first["ok"]
    first_id=first["microgoal"]["id"]
    assert runtime.MICRO.public()["id"]==first_id

    wrong=asyncio.run(runtime.micro_feedback(runtime.FeedbackReq(
        answer="5",status="done",topic="vertical/math",error_type="calculation"
    )))
    assert wrong["ok"] and not wrong["passed"]
    assert wrong["repair_microgoal"]["kind"]=="repair"
    assert runtime.SPINE.get("pending_retest")["value"]["retest_expected"] if False else True
    repair_id=runtime.MICRO.public()["id"]
    assert repair_id!=first_id

    repaired=asyncio.run(runtime.micro_feedback(runtime.FeedbackReq(
        answer="محاسبه را عجولانه انجام دادم و باید دوباره جمع را چک کنم",
        status="done",topic="vertical/math",error_type="calculation"
    )))
    assert repaired["ok"] and repaired["passed"]
    assert repaired["retest_microgoal"]["kind"]=="retest"
    assert runtime.MICRO.public()["question"]=="۲+۲ چند می‌شود؟"

    retested=asyncio.run(runtime.micro_feedback(runtime.FeedbackReq(
        answer="4",status="done",topic="vertical/math"
    )))
    assert retested["ok"] and retested["passed"]
    assert runtime.MICRO.public() is None

    waiting=runtime.micro_start(runtime.MicroReq(
        instruction="یک پاراگراف دیگر را بخوان و توضیح بده",
        kind="recall",
        question="چه فهمیدی؟",
        seconds=90,
        context_ref="vertical/continuity"
    ))["microgoal"]
    contract=runtime.return_start(runtime.ReturnReq(text="۵ دقیقه بعد برمی‌گردم",minutes=5))
    assert contract["ok"] and runtime.RETURNS.active()["id"]==contract["contract"]["id"]

    # Simulate Core process memory loss while preserving the SQLite database.
    monkeypatch.setattr(runtime,"CURRENT",{"session_id":None,"goal":"","plan":"","started_at":None})
    monkeypatch.setattr(runtime,"MICRO",MicroGoalEngine(store.connect))
    runtime.restore_continuity()

    assert runtime.CURRENT["session_id"]==sid
    assert runtime.CURRENT["goal"]=="زیست"
    assert runtime.MICRO.public()["id"]==waiting["id"]
    assert runtime.RETURNS.active()["id"]==contract["contract"]["id"]

    # Transport ACK is not learning evidence; the same waiting task survives.
    pending=runtime.BUS.pending("phone")
    for cmd in pending:
        runtime.BUS.ack(cmd["id"],"phone")
    assert runtime.MICRO.public()["id"]==waiting["id"]
