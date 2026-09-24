from __future__ import annotations
import time,json

class LearningPulse:
    def __init__(self,db_factory): self.db_factory=db_factory
    def score(self,attention_score:float,window_seconds=600):
        c=self.db_factory();rows=c.execute("select passed,confidence from learning_evidence where ts>=? order by id desc limit 20",(int(time.time())-int(window_seconds),)).fetchall();c.close()
        if not rows:return {"score":round(float(attention_score)*.30,1),"verified":0,"attempts":0,"label":"insufficient-evidence"}
        attempts=len(rows);weighted=sum((1 if r["passed"] else 0)*(.5+.5*float(r["confidence"] or 0)) for r in rows)
        evidence=weighted/max(1,attempts);score=max(0,min(100,float(attention_score)*.30+evidence*70))
        return {"score":round(score,1),"verified":sum(1 for r in rows if r["passed"]),"attempts":attempts,
                "label":"strong" if score>=78 else ("building" if score>=55 else "weak")}


class LearningModel:
    """Student model + error genome + repair/retest + spaced review."""
    def __init__(self,db_factory,event_bus=None):
        self.db_factory=db_factory;self.events=event_bus

    def observe(self,topic:str,passed:bool,error_type="",now:int|None=None):
        topic=(topic or "").strip()
        if not topic:return {"ok":False,"reason":"topic-required"}
        now=int(now or time.time());c=self.db_factory()
        old=c.execute("select * from student_topics where topic=?",(topic,)).fetchone()
        attempts=(int(old["attempts"] or 0)+1) if old else 1
        correct=(int(old["correct"] or 0)+(1 if passed else 0)) if old else (1 if passed else 0)
        mastery=(correct+1)/(attempts+2)
        next_due=now+self._interval(attempts,correct,passed)
        c.execute("""insert into student_topics(topic,updated_at,attempts,correct,mastery,last_error,next_due)
                     values(?,?,?,?,?,?,?) on conflict(topic) do update set updated_at=excluded.updated_at,
                     attempts=excluded.attempts,correct=excluded.correct,mastery=excluded.mastery,
                     last_error=excluded.last_error,next_due=excluded.next_due""",
                  (topic,now,attempts,correct,mastery,error_type if not passed else "",next_due))
        reason="repair-retest" if not passed else "spaced-review"
        due=now+15*60 if not passed else next_due
        c.execute("insert into review_queue(topic,due_at,reason,strength,attempts,status) values(?,?,?,?,?,?)",
                  (topic,due,reason,mastery,attempts,"pending"))
        if error_type:
            row=c.execute("select count,recent_count from error_genome where error_type=?",(error_type,)).fetchone()
            count=(int(row["count"])+1) if row else 1;recent=(int(row["recent_count"])+1) if row else 1
            c.execute("""insert into error_genome(error_type,updated_at,count,recent_count,last_topic,last_seen)
                         values(?,?,?,?,?,?) on conflict(error_type) do update set updated_at=excluded.updated_at,
                         count=excluded.count,recent_count=excluded.recent_count,last_topic=excluded.last_topic,last_seen=excluded.last_seen""",
                      (error_type,now,count,recent,topic,now))
        c.commit();c.close()
        if self.events:self.events.emit("learning.evidence",{"topic":topic,"passed":bool(passed),"error_type":error_type,
                         "mastery":round(mastery,3),"next_due":next_due},"core",topic,attempts)
        return {"ok":True,"topic":topic,"attempts":attempts,"correct":correct,"mastery":round(mastery,3),
                "next_due":next_due,"repair_due":(now+15*60) if not passed else None}

    def due_reviews(self,now:int|None=None,limit=20):
        now=int(now or time.time());c=self.db_factory()
        rows=c.execute("""select * from review_queue where status='pending' and due_at<=?
                          order by due_at asc limit ?""",(now,int(limit))).fetchall();c.close()
        return [dict(r) for r in rows]

    def mark_review_done(self,review_id:int):
        c=self.db_factory();c.execute("update review_queue set status='done' where id=?",(int(review_id),));c.commit();c.close()

    def student(self,limit=100):
        c=self.db_factory();rows=c.execute("select * from student_topics order by mastery asc,updated_at desc limit ?",(int(limit),)).fetchall();c.close()
        return [dict(r) for r in rows]

    def errors(self,limit=30):
        c=self.db_factory();rows=c.execute("select * from error_genome order by recent_count desc,count desc limit ?",(int(limit),)).fetchall();c.close()
        return [dict(r) for r in rows]

    def update_behavior(self,key:str,value,confidence=.6,evidence_count=1):
        now=int(time.time());c=self.db_factory();old=c.execute("select evidence_count from behavior_model where key=?",(key,)).fetchone()
        count=(int(old["evidence_count"] or 0)+int(evidence_count)) if old else int(evidence_count)
        c.execute("""insert into behavior_model(key,updated_at,value,confidence,evidence_count) values(?,?,?,?,?)
                     on conflict(key) do update set updated_at=excluded.updated_at,value=excluded.value,
                     confidence=excluded.confidence,evidence_count=excluded.evidence_count""",
                  (key,now,json.dumps(value,ensure_ascii=False),float(confidence),count));c.commit();c.close()

    def behavior(self,limit=50):
        c=self.db_factory();rows=c.execute("select * from behavior_model order by confidence desc,evidence_count desc limit ?",(int(limit),)).fetchall();c.close()
        out=[]
        for r in rows:
            d=dict(r)
            try:d["value"]=json.loads(d["value"])
            except Exception:pass
            out.append(d)
        return out

    @staticmethod
    def _interval(attempts:int,correct:int,passed:bool):
        if not passed:return 15*60
        ladder=[15*60,2*3600,8*3600,24*3600,3*86400,7*86400,14*86400,30*86400]
        return ladder[min(len(ladder)-1,max(0,correct-1))]
