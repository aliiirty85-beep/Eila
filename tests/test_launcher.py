import socket
import launcher


def test_port_open_detects_listener():
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.bind(("127.0.0.1",0));s.listen(1)
    try:
        port=s.getsockname()[1]
        assert launcher.port_open("127.0.0.1",port)
    finally:
        s.close()


def test_launcher_exits_cleanly_if_eila_already_healthy(monkeypatch):
    monkeypatch.setattr(launcher,"port_open",lambda host,port:True)
    monkeypatch.setattr(launcher,"healthy_existing",lambda port:True)
    monkeypatch.setattr(launcher,"run_core",lambda *a:(_ for _ in ()).throw(AssertionError("must not launch duplicate")))
    assert launcher.main()==0


def test_launcher_refuses_unknown_port_conflict_without_restart_loop(monkeypatch):
    monkeypatch.setattr(launcher,"port_open",lambda host,port:True)
    monkeypatch.setattr(launcher,"healthy_existing",lambda port:False)
    monkeypatch.setattr(launcher,"run_core",lambda *a:(_ for _ in ()).throw(AssertionError("must not launch into conflict")))
    assert launcher.main()==3
