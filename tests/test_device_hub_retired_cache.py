from pathlib import Path
from tempfile import TemporaryDirectory

from app.device_hub import DeviceHub
from app.storage import Storage


def test_retired_live_device_is_hidden_from_active_device_listing():
    td = TemporaryDirectory()
    try:
        storage = Storage(Path(td.name) / "eila.db")
        storage.init()
        hub = DeviceHub(storage.connect, stale_seconds=15)

        hub.heartbeat("old-laptop", "laptop", "Old", {"screen": True}, {}, "old-hw")
        retired = hub.retire("old-laptop")
        assert retired["ok"]

        # Regression: retired devices must not reappear from the in-memory live cache.
        assert hub.devices() == []
        assert hub.devices(include_retired=True)[0]["status"] == "retired"
    finally:
        td.cleanup()
