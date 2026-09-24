from __future__ import annotations
import re,time,json

class MicroGoalEngine:
    def __init__(self,db_factory,default_seconds=60,min_seconds=20,max_seconds=180):
        self.db_factory=db_factory;self.default_seconds=int(default_seconds);self.min_seconds=int(min_seconds);self.max_seconds=int(max_seconds);self.current=None;self.streak=0

    def start(self,session_id:int,instruction:str,kind="study",question="",expected="",source="manual",seconds=None,engagement_style="",display_instruction="",salience="",context_ref=""):
        if self.current and self.current.get("status")=="waiting":return self.public()
        now=int(time.time());secs=max(self.min_seconds,min(self.max_seconds,int(seconds or self.default_seconds)));c=self.db_factory()
        cur=c.execute("""insert into microgoals(session_id,created_at,deadline_at,kind,instruction,question,expected,source,status,
          engagement_style,display_instruction,salience,context_ref) values(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (session_id,now,now+secs,kind,instruction,question,expected,source,"waiting",engagement_style,display_instruction or instruction,salience,context_ref))
        c.commit();gid=int(cur.lastrowid);c.close()
        self.current={"id":gid,"session_id":session_id,"created_at":now,"deadline_at":now+secs,"kind":kind,"instruction":instruction,"question":question,
                      "expected":expected,"source":source,"status":"waiting","engagement_style":engagement_style,"display_instruction":display_instruction or instruction,
                      "salience":salience,"context_ref":context_ref}
        return self.public()

    def public(self):
        if not self.current:return None
        d=dict(self.current);d.pop("expected",None);d["remaining_seconds"]=max(0,int(self.current["deadline_at"]-time.time()));d["streak"]=self.streak;return d

    def tick(self):
        if self.current and self.current["status"]=="waiting" and time.time()>self.current["deadline_at"]:self._finish("expired","",False,"deadline")
        return self.public()

    @staticmethod
    def _norm(x):return re.sub(r"\s+"," ",(x or "").strip().lower()).replace("گزینه","").strip()

    def feedback(self,answer="",status="done",note="",confidence=.5,latency_ms=0,topic="",error_type=""):
        if not self.current:return {"ok":False,"reason":"no-active-microgoal"}
        expected=self._norm(self.current.get("expected",""));got=self._norm(answer)
        if status in ("failed","wrong","stuck"):passed=False
        elif expected and got:passed=(got==expected or got in expected or expected in got)
        else:passed=(status=="done")
        finished=dict(self.current);self._finish("done" if passed else "failed",answer,passed,note)
        c=self.db_factory();c.execute("""insert into learning_evidence(ts,session_id,microgoal_id,kind,passed,confidence,latency_ms,topic,error_type,metadata)
          values(?,?,?,?,?,?,?,?,?,?)""",(int(time.time()),finished.get("session_id"),finished.get("id"),finished.get("kind","study"),int(bool(passed)),
          float(confidence),int(latency_ms),topic,error_type,json.dumps({"note":note},ensure_ascii=False)));c.commit();c.close()
        return {"ok":True,"passed":bool(passed),"status":"done" if passed else "failed","streak":self.streak,"finished":finished,"style":finished.get("engagement_style","")}

    def _finish(self,status,answer,passed,note):
        if not self.current:return
        c=self.db_factory();c.execute("update microgoals set status=?,answer=?,result_note=? where id=?",(status,answer,note,self.current["id"]));c.commit();c.close()
        self.streak=self.streak+1 if passed else 0;self.current=None

    def restore(self,session_id,max_age_seconds=900):
        c=self.db_factory();r=c.execute("select * from microgoals where session_id=? and status='waiting' order by id desc limit 1",(session_id,)).fetchone();c.close()
        if not r:return None
        d=dict(r)
        if time.time()-d["created_at"]>max_age_seconds:return None
        self.current=d;return self.public()
