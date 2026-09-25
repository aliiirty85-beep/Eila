import start_eila


def test_one_click_reuses_healthy_core(monkeypatch):
    monkeypatch.setattr(start_eila,"health",lambda timeout=1.5:{"ok":True})
    monkeypatch.setattr(start_eila,"launch_core",lambda:(_ for _ in ()).throw(AssertionError("duplicate core")))
    monkeypatch.setattr(start_eila,"backup_via_core",lambda:{"ok":True})
    monkeypatch.setattr(start_eila,"token",lambda:"secret")
    monkeypatch.setattr(start_eila,"lan_ip",lambda:"192.168.1.10")
    monkeypatch.setattr(start_eila.webbrowser,"open",lambda *a,**k:True)
    assert start_eila.main()==0


def test_one_click_refuses_unknown_port_owner(monkeypatch):
    monkeypatch.setattr(start_eila,"health",lambda timeout=1.5:None)
    monkeypatch.setattr(start_eila,"port_open",lambda *a,**k:True)
    monkeypatch.setattr(start_eila,"launch_core",lambda:(_ for _ in ()).throw(AssertionError("must not launch")))
    monkeypatch.setattr(start_eila,"tail",lambda *a,**k:"")
    assert start_eila.main()==3
