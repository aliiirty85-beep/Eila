from __future__ import annotations
import time

class ReturnContractManager:
    def __init__(self,db_factory,bus,cfg):
        self.db_factory=db_factory;self.bus=bus;self.stages=list(cfg.get("return_escalation_seconds",[0,30,90,180]))
    def create(self,text,minutes=None,due_at=None):
        now=int(time.time())
        if due_at is None:
            if minutes is None:raise ValueError("minutes or due_at required")
            due_at=now+max(1,int(float(minutes)*60))
        c=self.db_factory();cur=c.execute("insert into return_contracts(created_at,due_at,text,status,last_stage) values(?,?,?,?,?)",(now,int(due_at),text.strip() or "برگشت به مطالعه","pending",-1))
        c.commit();cid=int(cur.lastrowid);c.close()
        self.bus.queue("schedule_return",{"contract_id":cid,"due_at":int(due_at),"text":text},ttl_seconds=max(900,int(due_at-now)+3600))
        return {"id":cid,"due_at":int(due_at),"text":text,"status":"pending"}
    def active(self):
        c=self.db_factory();r=c.execute("select * from return_contracts where status='pending' order by id desc limit 1").fetchone();c.close();return dict(r) if r else None
    def acknowledge(self,contract_id=None):
        c=self.db_factory()
        if contract_id is None:
            r=c.execute("select id from return_contracts where status='pending' order by id desc limit 1").fetchone()
            if not r:c.close();return {"ok":False,"reason":"no-active-contract"}
            contract_id=int(r["id"])
        c.execute("update return_contracts set status='done',acknowledged_at=? where id=?",(int(time.time()),int(contract_id)));c.commit();c.close()
        self.bus.queue("return_ack",{"contract_id":int(contract_id)},ttl_seconds=300);return {"ok":True,"contract_id":int(contract_id)}
    def tick(self):
        now=int(time.time());actions=[];c=self.db_factory();rows=c.execute("select * from return_contracts where status='pending' and due_at<=? order by due_at",(now,)).fetchall()
        for r in rows:
            overdue=now-int(r["due_at"]);stage=-1
            for i,sec in enumerate(self.stages):
                if overdue>=int(sec):stage=i
            if stage<=int(r["last_stage"]):continue
            texts=["ایلا: زمان برگشت رسید. برگرد سر مأموریت.","ایلا: هنوز منتظرم. وقفه تمام شده؛ فقط برگرد.","ایلا: برگشت عقب افتاده. همین الان یک حرکت کوچک: برگرد.","ایلا: وقفه دارد کش پیدا می‌کند. بدون مذاکره برگرد؛ فقط یک micro-goal."]
            kind="notify" if stage==0 else ("vibrate" if stage==1 else "speak")
            self.bus.queue(kind,{"text":texts[min(stage,3)],"contract_id":r["id"]},ttl_seconds=300);c.execute("update return_contracts set last_stage=? where id=?",(stage,r["id"]));actions.append({"contract_id":r["id"],"stage":stage,"kind":kind})
        c.commit();c.close();return actions
