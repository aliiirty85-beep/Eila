from __future__ import annotations
import time

class LearningPulse:
    def __init__(self,db_factory): self.db_factory=db_factory
    def score(self,attention_score:float,window_seconds=600):
        c=self.db_factory(); rows=c.execute("select passed,confidence from learning_evidence where ts>=? order by id desc limit 20",(int(time.time())-int(window_seconds),)).fetchall(); c.close()
        if not rows: return {"score":round(float(attention_score)*.30,1),"verified":0,"attempts":0,"label":"insufficient-evidence"}
        attempts=len(rows); weighted=sum((1 if r["passed"] else 0)*(.5+.5*float(r["confidence"] or 0)) for r in rows)
        evidence=weighted/max(1,attempts); score=max(0,min(100,float(attention_score)*.30+evidence*70))
        return {"score":round(score,1),"verified":sum(1 for r in rows if r["passed"]),"attempts":attempts,"label":"strong" if score>=78 else ("building" if score>=55 else "weak")}
