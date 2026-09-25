from __future__ import annotations
"""Test-gated bridge from Eila proposals to an optional local/open coding agent.

The live tree is never edited by the agent. A disposable candidate copy is used.
Existing safety/identity files, workflows and regression tests are immutable gates.
New tests are allowed; auto-promotion is intentionally forbidden.
"""
from pathlib import Path
import hashlib,json,os,shlex,shutil,subprocess,sys,time

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"data"/"maintenance"

def db_connect():
    import sqlite3
    db=ROOT/"data"/"eila.db"
    if not db.exists():return None
    c=sqlite3.connect(db);c.row_factory=sqlite3.Row
    return c

def newest_task():
    c=db_connect()
    if c is None:return None
    m=c.execute("""select id,created_at,'maintenance' task_type,title,rationale body
                   from maintenance_proposals where status='proposed'
                   order by created_at desc limit 1""").fetchone()
    q=c.execute("""select request_id id,created_at,'capability' task_type,
                          request_text title,spec body
                   from capability_requests where status='proposed'
                   order by created_at desc limit 1""").fetchone()
    c.close()
    candidates=[dict(x) for x in (m,q) if x]
    return max(candidates,key=lambda x:x["created_at"]) if candidates else None

def ignore(_dir,names):
    skip={".git",".venv","__pycache__",".pytest_cache","data","logs"}
    return [n for n in names if n in skip or n.endswith(".pyc")]

def run(cmd,cwd,timeout=1800,shell=False):
    return subprocess.run(cmd,cwd=cwd,shell=shell,text=True,capture_output=True,timeout=timeout)

def digest(path:Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def immutable_baseline(root:Path):
    files=[]
    for rel in ("app/constitution.py","app/security.py"):
        p=root/rel
        if p.exists():files.append(p)
    wf=root/".github"/"workflows"
    if wf.exists():files.extend(p for p in wf.rglob("*") if p.is_file())
    tests=root/"tests"
    if tests.exists():files.extend(p for p in tests.rglob("*.py") if p.is_file())
    return {str(p.relative_to(root)):digest(p) for p in files}

def immutable_changes(before:dict,candidate:Path):
    bad=[]
    for rel,h in before.items():
        p=candidate/rel
        if not p.exists() or digest(p)!=h:bad.append(rel)
    return bad

def update_task_status(task,status):
    c=db_connect()
    if c is None:return
    if task["task_type"]=="maintenance":
        c.execute("update maintenance_proposals set status=? where id=?",(status,int(task["id"])))
    else:
        c.execute("update capability_requests set status=? where request_id=?",(status,str(task["id"])))
    c.commit();c.close()

def main():
    task=newest_task()
    if not task:
        print("No maintenance/capability proposal waiting.")
        return 0

    template=os.getenv("EILA_CODING_AGENT_CMD","").strip()
    if not template:
        print("EILA_CODING_AGENT_CMD is not configured. Task remains queued.")
        return 2

    stamp=time.strftime("%Y%m%d-%H%M%S")
    work=DATA/"candidates"/stamp
    work.parent.mkdir(parents=True,exist_ok=True)
    baseline=immutable_baseline(ROOT)
    shutil.copytree(ROOT,work,ignore=ignore)

    body=task["body"]
    if task["task_type"]=="capability":
        try:body=json.dumps(json.loads(body),ensure_ascii=False,indent=2)
        except Exception:pass
    task_file=work/"MAINTENANCE_TASK.md"
    task_file.write_text(
        "# Eila isolated candidate task\n\n"
        f"Type: {task['task_type']}\nTitle/request: {task['title']}\n\n"
        "Rules:\n"
        "- Work only inside this disposable copy.\n"
        "- Preserve Eila Constitution and security rules.\n"
        "- Do not edit existing regression tests or GitHub workflows; add new tests instead.\n"
        "- Make the smallest reversible change that satisfies the evidence/request.\n"
        "- No critical paid-API dependency.\n"
        "- Add failure/rollback behavior.\n\n"
        "Task body/spec:\n"+str(body),
        encoding="utf-8"
    )

    command=template.replace("{prompt_file}",shlex.quote(str(task_file))).replace("{workdir}",shlex.quote(str(work)))
    print("Running candidate agent in:",work)
    agent=run(command,work,timeout=1800,shell=True)
    (work/"agent.stdout.txt").write_text(agent.stdout or "",encoding="utf-8")
    (work/"agent.stderr.txt").write_text(agent.stderr or "",encoding="utf-8")
    if agent.returncode!=0:
        update_task_status(task,"candidate-agent-failed")
        print("Agent failed; live Eila unchanged.")
        return agent.returncode

    bad=immutable_changes(baseline,work)
    if bad:
        update_task_status(task,"candidate-rejected-protected-change")
        print("Rejected: immutable gate files changed:",bad)
        return 4

    checks=[
        [sys.executable,"-m","compileall","-q","app","launcher.py","doctor.py","tests"],
        [sys.executable,"-m","pytest","-q"]
    ]
    if shutil.which("gradle") and (work/"android").exists():
        checks.append(["gradle","assembleDebug","--stacktrace"])
    report=[]
    for cmd in checks:
        cwd=work/"android" if cmd[0]=="gradle" else work
        p=run(cmd,cwd,timeout=1200,shell=False)
        report.append({"cmd":cmd,"cwd":str(cwd),"code":p.returncode,
                       "stdout":p.stdout[-12000:],"stderr":p.stderr[-12000:]})
        if p.returncode!=0:
            (work/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
            update_task_status(task,"candidate-rejected-tests")
            print("Candidate rejected by validation. Live Eila unchanged.")
            return 5

    (work/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    update_task_status(task,"candidate-passed-local-gates")
    print("Candidate passed local gates:",work)
    print("NOT promoted. Human/Codex review + CI + rollback snapshot are still required.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
