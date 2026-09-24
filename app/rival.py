from __future__ import annotations
import time

class RivalEngine:
    def __init__(self,db_factory,multiplier=1.07,round_seconds=600): self.db_factory=db_factory; self.multiplier=float(multiplier); self.round_seconds=int(round_seconds)
    def state(self,session_id):
        c=self.db_factory(); r=c.execute("select * from rival_rounds where session_id=? order by round_index desc limit 1",(session_id,)).fetchone(); c.close()
        if not r:return None
        d=dict(r); d["remaining_seconds"]=max(0,self.round_seconds-int(time.time()-d["started_at"])); return d
    def ensure_round(self,session_id):
        st=self.state(session_id)
        if st and st["remaining_seconds"]>0:return st
        c=self.db_factory(); idx=c.execute("select coalesce(max(round_index),0)+1 from rival_rounds where session_id=?",(session_id,)).fetchone()[0]
        c.execute("insert into rival_rounds(session_id,round_index,started_at) values(?,?,?)",(session_id,idx,int(time.time()))); c.commit(); c.close(); return self.state(session_id)
    def add_user_score(self,session_id,delta):
        st=self.ensure_round(session_id); target=max(0,float(st["user_score"])+float(delta))*self.multiplier
        c=self.db_factory(); c.execute("update rival_rounds set user_score=user_score+?,rival_score=? where id=?",(float(delta),target,st["id"])); c.commit(); c.close(); return self.state(session_id)
