from __future__ import annotations
import json,time,uuid

class EventBus:
    """Append-only idempotent event log shared by Eila nodes."""
    def __init__(self,db_factory): self.db_factory=db_factory

    def emit(self,kind:str,payload:dict|None=None,source_device="core",entity_id="",entity_version=0,event_id:str|None=None):
        eid=event_id or str(uuid.uuid4());now=int(time.time())
        body=json.dumps(payload or {},ensure_ascii=False,separators=(",",":"))
        c=self.db_factory()
        c.execute("""insert or ignore into events(event_id,created_at,source_device,kind,entity_id,entity_version,payload)
                     values(?,?,?,?,?,?,?)""",(eid,now,source_device,kind,entity_id,int(entity_version or 0),body))
        r=c.execute("select * from events where event_id=?",(eid,)).fetchone()
        c.commit();c.close()
        return self._row(r)

    def ingest(self,event:dict):
        eid=str(event.get("event_id") or "").strip();kind=str(event.get("kind") or "").strip()
        if not eid or not kind:return {"ok":False,"reason":"event_id-and-kind-required"}
        duplicate=self.get(eid) is not None
        row=self.emit(kind,event.get("payload") or {},str(event.get("source_device") or "unknown"),
                      str(event.get("entity_id") or ""),int(event.get("entity_version") or 0),eid)
        return {"ok":True,"duplicate":duplicate,"event":row}

    def get(self,event_id:str):
        c=self.db_factory();r=c.execute("select * from events where event_id=?",(event_id,)).fetchone();c.close()
        return self._row(r) if r else None

    def list_since(self,seq:int=0,limit:int=200):
        c=self.db_factory()
        rows=c.execute("select * from events where seq>? order by seq asc limit ?",
                       (int(seq),max(1,min(1000,int(limit))))).fetchall()
        c.close();return [self._row(r) for r in rows]

    def ack(self,event_id:str,device_id:str):
        c=self.db_factory()
        c.execute("insert or replace into event_acks(event_id,device_id,acked_at) values(?,?,?)",
                  (event_id,device_id,int(time.time())))
        c.commit();c.close()

    @staticmethod
    def _row(r):
        if not r:return None
        d=dict(r)
        try:d["payload"]=json.loads(d["payload"])
        except Exception:d["payload"]={}
        return d
