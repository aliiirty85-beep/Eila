from __future__ import annotations
import os, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LOG=ROOT/"logs"/"launcher.log"; LOG.parent.mkdir(exist_ok=True)

def log(msg):
    line=f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line,flush=True)
    with LOG.open("a",encoding="utf-8") as f: f.write(line+"\n")

def main():
    crashes=[]
    while True:
        now=time.time(); crashes=[t for t in crashes if now-t<300]
        safe=len(crashes)>=3
        env=os.environ.copy()
        if safe: env["EILA_SAFE_MODE"]="1"
        log("Starting Eila"+(" [SAFE MODE]" if safe else ""))
        try:
            code=subprocess.call([sys.executable,"-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8765"],cwd=ROOT,env=env)
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            log(f"launcher exception: {type(e).__name__}: {e}")
            code=1
        if code==0: return 0
        crashes.append(time.time())
        delay=min(30,2**min(4,len(crashes)))
        log(f"Core stopped with code {code}; restart in {delay}s")
        time.sleep(delay)

if __name__=="__main__":
    raise SystemExit(main())
