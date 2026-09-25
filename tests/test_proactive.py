import asyncio
import time
from types import SimpleNamespace

import pytest
from app import main as core
from app.storage import Storage
from app.command_bus import CommandBus
from app.microgoals import MicroGoalEngine
from app.sync import EventBus, SpineState


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    store = Storage(tmp_path / 'test.db')
    store.init()
    monkeypatch.setattr(core, 'STORAGE', store)
    monkeypatch.setattr(core, 'BUS', CommandBus(store.connect))
    monkeypatch.setattr(core, 'MICRO', MicroGoalEngine(store.connect))
    monkeypatch.setattr(core, 'SPINE', SpineState(store.connect, EventBus(store.connect)))
    monkeypatch.setattr(core, 'CURRENT', dict(session_id=None, goal='', plan='', started_at=None))
    monkeypatch.setattr(core, 'STATE', dict(flow=False, risk={'level': 'low'}))
    monkeypatch.setattr(core, 'VERIFIER', SimpleNamespace(status=lambda: None))
    monkeypatch.setattr(core, 'RETURNS', SimpleNamespace(active=lambda: None))
    monkeypatch.setattr(core, 'HUB', SimpleNamespace(primary_gaze=lambda: (None, None)))
    monkeypatch.setattr(core, 'ENG', core.EngagementEngine(store.connect))
    monkeypatch.setattr(core, 'FOCUS', core.FocusEngine({}))
    monkeypatch.setattr(core, 'LAST_AUTOGOAL', 0)
    monkeypatch.setattr(core, 'policy_actions', lambda *a: {})
    async def no_source(*a, **kw):
        return {'ok': False}
    monkeypatch.setattr(core, 'QUESTIONS', SimpleNamespace(from_gaze=no_source))
    return core


def test_idle_initiates_once_without_user_message_or_session(runtime):
    asyncio.run(runtime.maybe_autogoal())
    items = runtime.BUS.pending('dashboard')
    assert len(items) == 1 and items[0]['kind'] == 'notify'
    assert runtime.CURRENT['session_id'] is None
    asyncio.run(runtime.maybe_autogoal())
    assert len(runtime.BUS.pending('dashboard')) == 1


def test_unanswered_goal_waits_and_reminder_survives_disconnect(runtime, monkeypatch):
    runtime.CURRENT['session_id'] = 1
    goal = runtime.MICRO.start(1, 'Explain the paragraph', question='What did you learn?')
    monkeypatch.setattr(time, 'time', lambda: goal['deadline_at'] + 40)
    runtime.MICRO.tick()
    assert runtime.MICRO.public()['id'] == goal['id']
    asyncio.run(runtime.maybe_autogoal())
    items = runtime.commands('phone')['commands']
    assert len(items) == 1 and items[0]['payload']['microgoal_id'] == goal['id']
    asyncio.run(runtime.maybe_autogoal())
    assert runtime.commands('phone')['commands'] == items
    # Late reconnect receives the pending reminder; transport ACK is not an answer.
    runtime.BUS.ack(items[0]['id'], 'phone')
    assert runtime.commands('phone')['commands'] == []
    assert runtime.MICRO.current['id'] == goal['id']
    restored = MicroGoalEngine(runtime.db)
    assert restored.restore(1, max_age_seconds=1)['id'] == goal['id']
    assert runtime.MICRO.feedback()['reason'] == 'answer-required'
    assert runtime.MICRO.feedback('A concrete explanation')['ok']


@pytest.mark.parametrize('gate', ['stop', 'flow', 'activity', 'return'])
def test_quiet_gates_suppress_invitation_and_followup(runtime, monkeypatch, gate):
    if gate == 'stop':
        runtime.STORAGE.set_meta('proactive_stopped', True)
    elif gate == 'flow':
        runtime.STATE['flow'] = True
    elif gate == 'activity':
        runtime.VERIFIER.status = lambda: {'blocks_study': True}
    else:
        runtime.RETURNS.active = lambda: {'status': 'pending'}
    asyncio.run(runtime.maybe_autogoal())
    assert runtime.BUS.pending('phone') == []
    runtime.CURRENT['session_id'] = 1
    g = runtime.MICRO.start(1, 'Read')
    monkeypatch.setattr(time, 'time', lambda: g['deadline_at'] + 40)
    asyncio.run(runtime.maybe_autogoal())
    assert runtime.BUS.pending('phone') == []


def test_active_session_creates_goal_without_chat(runtime):
    runtime.CURRENT['session_id'] = 1
    asyncio.run(runtime.maybe_autogoal())
    assert runtime.MICRO.current['status'] == 'waiting'
    assert runtime.BUS.pending('phone')[0]['kind'] == 'microgoal'


def test_stop_during_ai_request_cannot_create_orphan_goal(runtime):
    runtime.CURRENT['session_id'] = 1
    async def stopped(*a, **kw):
        runtime.CURRENT['session_id'] = None
        return {'ok': False}
    runtime.QUESTIONS.from_gaze = stopped
    asyncio.run(runtime.maybe_autogoal())
    assert runtime.MICRO.current is None
    assert runtime.BUS.pending('phone') == []


def test_completed_goal_reminder_not_replayed_on_reconnect(runtime):
    runtime.BUS.queue('notify', {'text': 'old', 'microgoal_id': 999})
    assert runtime.commands('phone')['commands'] == []


def test_reminders_are_bounded_and_stop_survives_restart(runtime, monkeypatch):
    runtime.CURRENT['session_id'] = 1
    g = runtime.MICRO.start(1, 'Read')
    for overdue in (40, 45, 160, 300, 800):
        monkeypatch.setattr(time, 'time', lambda: g['deadline_at'] + overdue)
        asyncio.run(runtime.maybe_autogoal())
    assert len(runtime.commands('phone')['commands']) == 2
    runtime.BUS.queue('speak', {'text': 'Return', 'study_session_id': 1})
    monkeypatch.setattr(runtime, 'MEM', SimpleNamespace(session_summary=lambda sid: {'text': '', 'points': []}))
    monkeypatch.setattr(runtime, 'FIREWALL', SimpleNamespace(pending=lambda n: []))
    runtime.stop_session()
    runtime.restore_continuity()
    asyncio.run(runtime.maybe_autogoal())
    assert runtime.STORAGE.get_meta('proactive_stopped') is True
    assert runtime.MICRO.current is None
    assert [c['kind'] for c in runtime.commands('phone')['commands']] == ['clear_microgoal']


def test_scheduler_starts_invitation_without_an_http_message(runtime, monkeypatch):
    async def nothing():pass
    class EndTick(Exception):pass
    async def end_tick(seconds):raise EndTick()
    monkeypatch.setattr(runtime, 'ensure_core_node', lambda: None)
    monkeypatch.setattr(runtime.RETURNS, 'tick', lambda: None, raising=False)
    monkeypatch.setattr(runtime, 'auto_desktop_attention', nothing)
    monkeypatch.setattr(runtime, 'MAINT', SimpleNamespace(safe_tick=lambda *a: {}))
    monkeypatch.setattr(runtime.HUB, 'devices', lambda: [], raising=False)
    monkeypatch.setattr(runtime, 'AI', SimpleNamespace(health=lambda: {}))
    monkeypatch.setattr(runtime, 'LAST_BACKUP', time.time())
    monkeypatch.setattr(asyncio, 'sleep', end_tick)
    with pytest.raises(EndTick):asyncio.run(runtime.background_loop())
    assert 'last_error' not in runtime.STATE
    assert runtime.commands('dashboard')['commands'][0]['payload']['idle_invitation']
