from __future__ import annotations
import json,sys,urllib.request
from pathlib import Path
from app.storage import Storage
ROOT=Path(__file__).resolve().parent
def check(name,fn):
    try:return {"name":name,"ok":bool(fn()),"detail":""}
    except Exception as e:return {"name":name,"ok":False,"detail":f"{type(e).__name__}: {e}"}
def main():
    results=[]
    results.append(check("config",lambda:bool(json.loads((ROOT/"config.json").read_text(encoding="utf-8")))))
    s=Storage(ROOT/"data"/"eila.db");s.init();i=s.integrity();results.append({"name":"database","ok":i["ok"],"detail":i["detail"]})
    results.append(check("python>=3.11",lambda:sys.version_info>=(3,11)))
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags",timeout=2) as r:ok=r.status==200
    except Exception:ok=False
    results.append({"name":"ollama","ok":ok,"detail":"optional; online providers may be used instead"})
    print("Eila Doctor")
    for r in results:print(("[OK] " if r["ok"] else "[!!] ")+r["name"]+(" - "+r["detail"] if r["detail"] else ""))
    critical=all(r["ok"] for r in results if r["name"] in ("config","database","python>=3.11"));return 0 if critical else 1
if __name__=="__main__":raise SystemExit(main())
