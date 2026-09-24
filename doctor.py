from __future__ import annotations
import json,sys,urllib.request,time
from pathlib import Path
from app.storage import Storage,SCHEMA_VERSION

ROOT=Path(__file__).resolve().parent

def check(name,fn,detail=""):
    try:
        ok=bool(fn())
        return {"name":name,"ok":ok,"detail":detail}
    except Exception as e:
        return {"name":name,"ok":False,"detail":f"{type(e).__name__}: {e}"}

def main():
    results=[]
    cfg=json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
    results.append({"name":"config","ok":bool(cfg),"detail":f"version={cfg.get('version')} protocol={cfg.get('protocol_version')}"})
    results.append(check("python>=3.11",lambda:sys.version_info>=(3,11)))

    s=Storage(ROOT/"data"/"eila.db");s.init()
    integ=s.integrity()
    results.append({"name":"database-integrity","ok":integ["ok"],"detail":integ["detail"]})

    c=s.connect()
    schema_row=c.execute("select value from meta where key='schema_version'").fetchone()
    schema=int(schema_row[0]) if schema_row else 0
    tables={r[0] for r in c.execute("select name from sqlite_master where type='table'").fetchall()}
    c.close()
    required={"spine_state","spine_conflicts","events","behavior_policies","behavior_policy_history",
              "student_topics","error_genome","devices","device_snapshots"}
    results.append({"name":"schema","ok":schema==SCHEMA_VERSION,
                    "detail":f"db={schema} code={SCHEMA_VERSION}"})
    missing=sorted(required-tables)
    results.append({"name":"spine-tables","ok":not missing,
                    "detail":"" if not missing else "missing="+",".join(missing)})

    backups=sorted((ROOT/"data"/"backups").glob("eila-*.db"),key=lambda p:p.stat().st_mtime,reverse=True)
    if backups:
        age=int(time.time()-backups[0].stat().st_mtime)
        results.append({"name":"backup-present","ok":True,"detail":f"latest_age_seconds={age}"})
    else:
        results.append({"name":"backup-present","ok":False,"detail":"no backup yet; start Eila or run /api/backup"})

    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags",timeout=2) as r:ollama=r.status==200
    except Exception:ollama=False
    results.append({"name":"ollama","ok":ollama,"detail":"optional; online providers may be used instead"})

    print("Eila Doctor")
    for r in results:
        print(("[OK] " if r["ok"] else "[!!] ")+r["name"]+(" - "+r["detail"] if r["detail"] else ""))

    critical_names={"config","python>=3.11","database-integrity","schema","spine-tables"}
    critical=all(r["ok"] for r in results if r["name"] in critical_names)
    return 0 if critical else 1

if __name__=="__main__":
    raise SystemExit(main())
