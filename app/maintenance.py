from __future__ import annotations
import json,time
from pathlib import Path

class MaintenanceEngine:
    """Self-care without blind self-modification.

    Safe repairs happen automatically (backup/integrity housekeeping).
    Code-level changes are emitted as proposals/tasks so a test-gated coding agent
    can work on a disposable branch/copy instead of silently rewriting live code.
    """
    def __init__(self,db_factory,storage,ai,data_dir:Path,cfg:dict):
        self.db_factory=db_factory;self.storage=storage;self.ai=ai;self.data_dir=Path(data_dir);self.cfg=cfg
        self.last_tick=0.0;self.last_proposal=0.0;self.last_report={}

    def _event(self,kind,severity="info",detail="",repaired=False):
        c=self.db_factory();c.execute("insert into maintenance_events(ts,kind,severity,detail,repaired) values(?,?,?,?,?)",
          (int(time.time()),kind,severity,detail,int(bool(repaired))));c.commit();c.close()

    def safe_tick(self,devices=None,ai_health=None):
        interval=float(self.cfg.get("maintenance_interval_minutes",30))*60
        if time.time()-self.last_tick<interval:return self.last_report
        self.last_tick=time.time()
        report={"ts":int(time.time()),"database":self.storage.integrity(),"repairs":[],"warnings":[]}
        if not report["database"].get("ok"):
            r=self.storage.recover_latest_backup(self.data_dir/"backups")
            report["repairs"].append({"database_recovery":r});self._event("database-recovery","critical",json.dumps(r),r.get("ok"))
        else:
            try:
                p=self.storage.backup(self.data_dir/"backups",self.cfg.get("backup_keep",14))
                report["repairs"].append({"backup":p})
            except Exception as e:
                report["warnings"].append("backup:"+str(e));self._event("backup-failed","warning",str(e),False)
        stale=[d for d in (devices or []) if d.get("stale")]
        if stale:report["warnings"].append("stale-devices:"+",".join(d.get("device_id","?") for d in stale))
        if ai_health and all(not v for v in ai_health.get("models",{}).values()):
            report["warnings"].append("no-ai-models-configured")
        self.last_report=report
        return report

    async def propose_if_needed(self,health:dict):
        interval=float(self.cfg.get("maintenance_proposal_interval_hours",24))*3600
        if time.time()-self.last_proposal<interval:return None
        self.last_proposal=time.time()
        c=self.db_factory();rows=c.execute("""select kind,severity,detail from maintenance_events
                                             where ts>=? order by id desc limit 30""",(int(time.time())-86400,)).fetchall();c.close()
        issues=[dict(r) for r in rows if r["severity"] in ("warning","critical")]
        if not issues:return None
        prompt=("برای پروژه Eila یک maintenance proposal کوتاه و فنی بنویس. "
                "هیچ فایل live را تغییر نده. فقط root cause احتمالی، تست بازتولید، patch plan، regression tests و rollback plan. "
                "این پیشنهاد بعداً باید توسط coding agent روی branch/copy جدا تست شود.\nEvidence:\n"+
                json.dumps(issues,ensure_ascii=False))
        txt=await self.ai.ask("deep",[{"role":"user","content":prompt}],max_tokens=900)
        if txt.startswith("__AI_ERROR__"):return None
        c=self.db_factory();cur=c.execute("insert into maintenance_proposals(created_at,title,rationale,evidence) values(?,?,?,?)",
          (int(time.time()),"Auto-maintenance proposal",txt,json.dumps(issues,ensure_ascii=False)));c.commit();pid=int(cur.lastrowid);c.close()
        return {"id":pid,"proposal":txt}

    def status(self):
        c=self.db_factory()
        events=[dict(r) for r in c.execute("select * from maintenance_events order by id desc limit 20").fetchall()]
        proposals=[dict(r) for r in c.execute("select * from maintenance_proposals order by id desc limit 10").fetchall()]
        c.close()
        return {"last_report":self.last_report,"events":events,"proposals":proposals,
                "policy":"runtime self-heal automatic; code changes test-gated and staged"}
