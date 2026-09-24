from __future__ import annotations
import json,time

class SpineState:
    """Canonical identity/state independent of any one laptop or phone."""
    def __init__(self,db_factory,event_bus):
        self.db_factory=db_factory;self.events=event_bus

    def set(self,key:str,value,source_device="core",expected_revision:int|None=None):
        key=key.strip()
        if not key:return {"ok":False,"reason":"key-required"}
        now=int(time.time());body=json.dumps(value,ensure_ascii=False,separators=(",",":"))
        c=self.db_factory();row=c.execute("select revision from spine_state where key=?",(key,)).fetchone()
        current=int(row["revision"]) if row else 0
        if expected_revision is not None and current!=int(expected_revision):
            c.close();return {"ok":False,"reason":"revision-conflict","current_revision":current}
        rev=current+1
        c.execute("""insert into spine_state(key,revision,updated_at,source_device,value) values(?,?,?,?,?)
                     on conflict(key) do update set revision=excluded.revision,updated_at=excluded.updated_at,
                     source_device=excluded.source_device,value=excluded.value""",
                  (key,rev,now,source_device,body))
        c.commit();c.close()
        self.events.emit("spine.state.changed",{"key":key,"value":value},source_device,key,rev)
        return {"ok":True,"key":key,"revision":rev,"updated_at":now,"source_device":source_device,"value":value}

    def get(self,key:str,default=None):
        c=self.db_factory();r=c.execute("select * from spine_state where key=?",(key,)).fetchone();c.close()
        if not r:return default
        d=dict(r)
        try:d["value"]=json.loads(d["value"])
        except Exception:pass
        return d

    def snapshot(self):
        c=self.db_factory();rows=c.execute("select * from spine_state order by key").fetchall();c.close()
        out={}
        for r in rows:
            d=dict(r)
            try:v=json.loads(d["value"])
            except Exception:v=d["value"]
            out[d["key"]]={"revision":d["revision"],"updated_at":d["updated_at"],
                           "source_device":d["source_device"],"value":v}
        return out
