from __future__ import annotations
import json,os,socket,subprocess,sys,time,urllib.request,urllib.error,webbrowser
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"
HEALTH_URL="http://127.0.0.1:8765/api/health"
DASHBOARD_URL="http://127.0.0.1:8765/"

def health(timeout=1.5):
    try:
        with urllib.request.urlopen(HEALTH_URL,timeout=timeout) as r:
            if r.status!=200:return None
            data=json.loads(r.read().decode("utf-8","replace"))
            return data if data.get("ok") else None
    except Exception:
        return None

def port_open(host="127.0.0.1",port=8765,timeout=.35):
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.settimeout(timeout)
    try:return s.connect_ex((host,port))==0
    finally:s.close()

def backup_via_core():
    try:
        req=urllib.request.Request("http://127.0.0.1:8765/api/backup",data=b"{}",method="POST",
                                   headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=5) as r:
            return json.loads(r.read().decode("utf-8","replace"))
    except Exception as e:
        return {"ok":False,"reason":f"{type(e).__name__}: {e}"}

def tail(path:Path,lines=35):
    if not path.exists():return ""
    try:return "\n".join(path.read_text(encoding="utf-8",errors="replace").splitlines()[-lines:])
    except Exception:return ""

def token():
    from app.security import SecurityManager
    return SecurityManager(DATA).token

def lan_ip():
    # Route-based discovery first; no packet needs to be received.
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8",80))
        ip=s.getsockname()[0]
        if ip and not ip.startswith("127."):return ip
    except Exception:
        pass
    finally:
        s.close()
    try:
        ip=socket.gethostbyname(socket.gethostname())
        return ip if ip and not ip.startswith("127.") else None
    except Exception:
        return None

def launch_core():
    flags=0
    if os.name=="nt":flags=getattr(subprocess,"CREATE_NEW_CONSOLE",0)
    return subprocess.Popen([sys.executable,"launcher.py"],cwd=ROOT,creationflags=flags)

def main():
    print("Eila Start — one-click bootstrap")
    current=health()
    if current:
        print("[OK] Eila Core is already healthy.")
    else:
        if port_open():
            print("[STOP] Port 8765 is occupied but Eila health is not responding.")
            print("Nothing was killed automatically. Close the stale process or inspect logs/core.log.")
            print(tail(ROOT/"logs"/"core.log"))
            return 3
        print("[..] Starting Eila Core...")
        proc=launch_core()
        deadline=time.time()+35
        current=None
        while time.time()<deadline:
            current=health()
            if current:break
            if proc.poll() is not None:
                print(f"[FAIL] Eila launcher exited with code {proc.returncode}.")
                print(tail(ROOT/"logs"/"core.log"))
                return proc.returncode or 2
            time.sleep(.5)
        if not current:
            print("[FAIL] Core did not become healthy within 35 seconds.")
            print(tail(ROOT/"logs"/"core.log"))
            return 4
        print("[OK] Core health endpoint is responding.")

    b=backup_via_core()
    print("[OK] Initial backup created." if b.get("ok") else "[WARN] Backup request failed: "+str(b.get("reason") or b))
    print()
    t=token();ip=lan_ip()
    print("Pairing token:")
    print(t)
    print()
    if ip:
        print("Phone / tablet Server URL:")
        print(f"http://{ip}:8765")
        print()
    else:
        print("[WARN] LAN IP could not be determined automatically.")
        print()
    print("Dashboard:")
    print(DASHBOARD_URL)
    try:webbrowser.open(DASHBOARD_URL,new=2)
    except Exception:pass
    print("[READY] Eila is running. Keep the Eila Core window open.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
