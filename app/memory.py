from __future__ import annotations
import time

ALLOWED={"mastery","error","behavior","decision","context","commitment","preference"}

class MemoryManager:
    def __init__(self,db_factory): self.db_factory=db_factory
    def upsert(self,category,key,value,confidence=.6,source=""):
        category=category if category in ALLOWED else "context"; now=int(time.time()); c=self.db_factory()
        c.execute("""insert into memory_items(created_at,updated_at,category,key,value,confidence,source,active)
                     values(?,?,?,?,?,?,?,1)
                     on conflict(category,key) do update set updated_at=excluded.updated_at,value=excluded.value,
                     confidence=excluded.confidence,source=excluded.source,active=1""",(now,now,category,key,value,float(confidence),source))
        c.commit(); c.close()
    def relevant(self,limit=40):
        c=self.db_factory(); rows=c.execute("""select category,key,value,confidence,updated_at from memory_items
          where active=1 order by confidence desc,updated_at desc limit ?""",(int(limit),)).fetchall(); c.close(); return [dict(r) for r in rows]
    def session_summary(self,session_id):
        c=self.db_factory(); ev=c.execute("select kind,passed,topic,error_type from learning_evidence where session_id=? order by id",(session_id,)).fetchall(); c.close()
        if not ev:return {"text":"شواهد یادگیری کافی ثبت نشد.","points":[]}
        passed=sum(1 for r in ev if r["passed"]); attempts=len(ev); errors={}
        for r in ev:
            if r["error_type"]:errors[r["error_type"]]=errors.get(r["error_type"],0)+1
        best=max(errors,key=errors.get) if errors else ""; points=[f"{passed}/{attempts} شواهد یادگیری تأیید شد."]
        if best:points.append(f"پرتکرارترین نوع خطا: {best}.")
        return {"text":" ".join(points),"points":points}
