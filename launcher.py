from __future__ import annotations
import os,subprocess,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LOG=ROOT/"logs"/"launcher.log"
CORE_LOG=ROOT/"logs"/"core.log"
LOG.parent.mkdir(exist_ok=True)

def log(msg):
    line=f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line,flush=True)
    with LOG.open("a",encoding="utf-8") as f:
        f.write(line+"\n")

def run_core(env,host,port):
    cmd=[sys.executable,"-m","uvicorn","app.main:app","--host",host,"--port",port,"--log-level","debug"]
    with CORE_LOG.open("a",encoding="utf-8") as core:
        core.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} START =====\n")
        proc=subprocess.Popen(
            cmd,cwd=ROOT,env=env,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding="utf-8",errors="replace",bufsize=1
        )
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                print(line,end="",flush=True)
                core.write(line);core.flush()
        except KeyboardInterrupt:
            try:proc.terminate()
            except Exception:pass
            try:proc.wait(timeout=5)
            except Exception:
                try:proc.kill()
                except Exception:pass
            raise
        return proc.wait()

def main():
    crashes=[]
    while True:
        now=time.time()
        crashes=[t for t in crashes if now-t<300]
        safe=len(crashes)>=3
        env=os.environ.copy()
        if safe:env["EILA_SAFE_MODE"]="1"
        host=env.get("EILA_HOST","0.0.0.0")
        port=env.get("EILA_PORT","8765")
        log("Starting Eila"+(" [SAFE MODE]" if safe else ""))
        try:
            code=run_core(env,host,port)
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            log(f"launcher exception: {type(e).__name__}: {e}")
            code=1
        if code==0:return 0
        crashes.append(time.time())
        delay=min(30,2**min(4,len(crashes)))
        log(f"Core stopped with code {code}; restart in {delay}s")
        log(f"Detailed Core output: {CORE_LOG}")
        time.sleep(delay)

if __name__=="__main__":
    raise SystemExit(main())
