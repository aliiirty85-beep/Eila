from __future__ import annotations
import time

class StudyFirewall:
    def __init__(self,db_factory):self.db_factory=db_factory
    def defer(self,text:str,reason="unrelated"):
        c=self.db_factory()
        cur=c.execute("insert into later_inbox(created_at,text,reason,status) values(?,?,?,'pending')",(int(time.time()),text,reason))
        c.commit();i=int(cur.lastrowid);c.close();return i
    def pending(self,limit=50):
        c=self.db_factory();rows=c.execute("select * from later_inbox where status='pending' order by id desc limit ?",(int(limit),)).fetchall();c.close()
        return [dict(r) for r in rows]
    def clear(self,item_id:int):
        c=self.db_factory();c.execute("update later_inbox set status='done' where id=?",(int(item_id),));c.commit();c.close()
