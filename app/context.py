from __future__ import annotations
import time

class ContextRegistry:
    def __init__(self,db_factory): self.db_factory=db_factory
    def set(self,kind,title="",content="",ref=""):
        now=int(time.time()); c=self.db_factory(); c.execute("update context_sources set active=0 where active=1")
        cur=c.execute("insert into context_sources(created_at,updated_at,kind,title,content,ref,active) values(?,?,?,?,?,?,1)",(now,now,kind,title,content,ref))
        c.commit(); cid=int(cur.lastrowid); c.close(); return cid
    def current(self):
        c=self.db_factory(); r=c.execute("select * from context_sources where active=1 order by id desc limit 1").fetchone(); c.close()
        return dict(r) if r else None
