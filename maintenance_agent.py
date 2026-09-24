from __future__ import annotations
"""Optional test-gated bridge to a locally installed/open coding agent.

This script never gives an agent direct permission to rewrite the live Eila tree.
It copies the project into a disposable candidate directory, runs the configured
agent there, then runs syntax/tests. Promotion is deliberately separate so the
stable installation always has a rollback point.
"""
from pathlib import Path
import json,os,shlex,shutil,subprocess,sys,time

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"/"maintenance"
PROTECTED={"app/constitution.py","app/security.py",".env","data"}

def newest_proposal():
    db=ROOT/"data"/"eila.db"
    if not db.exists():return None
    import sqlite3
    c=sqlite3.connect(db);c.row_factory=sqlite3.Row
    r=c.execute("select * from maintenance_proposals where status='proposed' order by id desc limit 1").fetchone()
    c.close();return dict(r) if r else None

def ignore(_dir,names):
    skip={".git",".venv","__pycache__",".pytest_cache","data","logs"}
    return [n for n in names if n in skip or n.endswith(".pyc")]

def run(cmd,cwd,timeout=1800):
    return subprocess.run(cmd,cwd=cwd,shell=True,text=True,capture_output=True,timeout=timeout)

def changed_protected(live:Path,candidate:Path):
    bad=[]
    for rel in ("app/constitution.py","app/security.py"):
        a=live/rel;b=candidate/rel
        if a.exists() and b.exists() and a.read_bytes()!=b.read_bytes():bad.append(rel)
    return bad

def main():
    proposal=newest_proposal()
    if not proposal:
        print("No maintenance proposal waiting.")
        return 0
    template=os.getenv("EILA_CODING_AGENT_CMD","").strip()
    if not template:
        print("EILA_CODING_AGENT_CMD is not configured. Proposal remains queued.")
        return 2

    stamp=time.strftime("%Y%m%d-%H%M%S")
    work=DATA/"candidates"/stamp
    work.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT,work,ignore=ignore)
    task=work/"MAINTENANCE_TASK.md"
    task.write_text(
        "# Eila maintenance candidate\n\n"
        "Work only inside this disposable copy. Preserve Eila Constitution and security policy. "
        "Fix the evidenced problem with the smallest patch and add regression tests.\n\n"
        +proposal["rationale"],encoding="utf-8")

    command=template.replace("{prompt_file}",shlex.quote(str(task))).replace("{workdir}",shlex.quote(str(work)))
    print("Running candidate agent in:",work)
    agent=run(command,work)
    (work/"agent.stdout.txt").write_text(agent.stdout or "",encoding="utf-8")
    (work/"agent.stderr.txt").write_text(agent.stderr or "",encoding="utf-8")
    if agent.returncode!=0:
        print("Agent failed; live Eila unchanged.")
        return agent.returncode

    bad=changed_protected(ROOT,work)
    if bad:
        print("Rejected: protected files changed:",bad)
        return 4

    checks=[
        [sys.executable,"-m","compileall","-q","app","launcher.py","doctor.py","tests"],
        [sys.executable,"-m","pytest","-q"]
    ]
    report=[]
    for cmd in checks:
        p=subprocess.run(cmd,cwd=work,text=True,capture_output=True,timeout=900)
        report.append({"cmd":cmd,"code":p.returncode,"stdout":p.stdout[-8000:],"stderr":p.stderr[-8000:]})
        if p.returncode!=0:
            (work/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
            print("Candidate rejected by tests. Live Eila unchanged.")
            return 5

    (work/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Candidate passed local gates:",work)
    print("It is NOT auto-promoted. Review/CI/rollback snapshot remain required.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
