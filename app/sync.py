from __future__ import annotations
import json,time,uuid,os
from pathlib import Path

class EventBus:
    """Append-only event log. event_id makes retries safe across devices."""
    def __init__(self,db_factory): self.db_factory=db_factory

    def emit(self,kind:str,payload:dict|None=None,source_device="core",entity_id="",entity_version=0,event_id:str|None=None):
        eid=event_id or str(uuid.uuid4());now=int(time.time())
        body=json.dumps(payload or {},ensure_ascii=False,separators=(",",":"))
        c=self.db_factory()
        c.execute("""insert or ignore into events(event_id,created_at,source_device,kind,entity_id,entity_version,payload)
                     values(?,?,?,?,?,?,?)""",(eid,now,source_device,kind,entity_id,int(entity_version or 0),body))
        row=c.execute("select * from events where event_id=?",(eid,)).fetchone()
        c.commit();c.close()
        return self._row(row)

    def ingest(self,event:dict):
        eid=str(event.get("event_id") or "").strip();kind=str(event.get("kind") or "").strip()
        if not eid or not kind:return {"ok":False,"reason":"event_id-and-kind-required"}
        duplicate=self.get(eid) is not None
        row=self.emit(kind,event.get("payload") or {},str(event.get("source_device") or "unknown"),
                      str(event.get("entity_id") or ""),int(event.get("entity_version") or 0),eid)
        return {"ok":True,"duplicate":duplicate,"event":row}

    def get(self,event_id:str):
        c=self.db_factory();row=c.execute("select * from events where event_id=?",(event_id,)).fetchone();c.close()
        return self._row(row) if row else None

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
    def _row(row):
        if not row:return None
        d=dict(row)
        try:d["payload"]=json.loads(d["payload"])
        except Exception:d["payload"]={}
        return d


class SpineState:
    """Canonical Eila state independent of any specific laptop."""
    def __init__(self,db_factory,event_bus:EventBus):
        self.db_factory=db_factory;self.events=event_bus

    def set(self,key:str,value,source_device="core",expected_revision:int|None=None):
        key=key.strip()
        if not key:return {"ok":False,"reason":"key-required"}
        c=self.db_factory();row=c.execute("select revision from spine_state where key=?",(key,)).fetchone()
        current=int(row["revision"]) if row else 0
        if expected_revision is not None and current!=int(expected_revision):
            c.close();return {"ok":False,"reason":"revision-conflict","current_revision":current}
        rev=current+1;now=int(time.time())
        c.execute("""insert into spine_state(key,revision,updated_at,source_device,value) values(?,?,?,?,?)
                     on conflict(key) do update set revision=excluded.revision,updated_at=excluded.updated_at,
                     source_device=excluded.source_device,value=excluded.value""",
                  (key,rev,now,source_device,json.dumps(value,ensure_ascii=False,separators=(",",":"))))
        c.commit();c.close()
        self.events.emit("spine.state.changed",{"key":key,"value":value},source_device,key,rev)
        return {"ok":True,"key":key,"revision":rev,"updated_at":now,"source_device":source_device,"value":value}

    def get(self,key:str,default=None):
        c=self.db_factory();row=c.execute("select * from spine_state where key=?",(key,)).fetchone();c.close()
        if not row:return default
        d=dict(row)
        try:d["value"]=json.loads(d["value"])
        except Exception:pass
        return d

    def snapshot(self):
        c=self.db_factory();rows=c.execute("select * from spine_state order by key").fetchall();c.close()
        out={}
        for row in rows:
            d=dict(row)
            try:value=json.loads(d["value"])
            except Exception:value=d["value"]
            out[d["key"]]={"revision":d["revision"],"updated_at":d["updated_at"],
                           "source_device":d["source_device"],"value":value}
        return out

    def apply_remote(self,key:str,item:dict,source_device="remote"):
        key=key.strip();remote_rev=int(item.get("revision") or 0)
        if not key or remote_rev<=0:return {"ok":False,"reason":"bad-remote-state"}
        local=self.get(key)
        if local and int(local.get("revision") or 0)>=remote_rev:
            return {"ok":True,"applied":False,"reason":"local-newer-or-equal"}
        now=int(item.get("updated_at") or time.time());src=str(item.get("source_device") or source_device)
        value=item.get("value")
        c=self.db_factory()
        c.execute("""insert into spine_state(key,revision,updated_at,source_device,value) values(?,?,?,?,?)
                     on conflict(key) do update set revision=excluded.revision,updated_at=excluded.updated_at,
                     source_device=excluded.source_device,value=excluded.value""",
                  (key,remote_rev,now,src,json.dumps(value,ensure_ascii=False,separators=(",",":"))))
        c.commit();c.close()
        self.events.emit("spine.state.replicated",{"key":key,"remote_revision":remote_rev},source_device,key,remote_rev)
        return {"ok":True,"applied":True,"key":key,"revision":remote_rev}


class SyncManager:
    def __init__(self,db_factory,memory,protocol_version=3,event_bus:EventBus|None=None,spine:SpineState|None=None):
        self.db_factory=db_factory;self.memory=memory;self.protocol_version=int(protocol_version)
        self.events=event_bus or EventBus(db_factory)
        self.spine=spine or SpineState(db_factory,self.events)

    def snapshot(self,current,micro,return_contract,rival,research,policies=None,devices=None):
        events=self.events.list_since(0,500)
        return {
          "protocol_version":self.protocol_version,
          "server_ts":int(time.time()),
          "spine":self.spine.snapshot(),
          "session":dict(current),
          "microgoal":micro,
          "return_contract":return_contract,
          "memory":self.memory.relevant(120),
          "policies":policies or [],
          "devices":devices or [],
          "rival":rival,
          "research":research[:10],
          "events_tail":events
        }

    def store_offer(self,device_id:str,snapshot:dict):
        if int(snapshot.get("protocol_version",0))!=self.protocol_version:
            return {"ok":False,"reason":"protocol-mismatch","expected":self.protocol_version}
        now=int(time.time());c=self.db_factory()
        c.execute("""insert into device_snapshots(device_id,received_at,snapshot)
                     values(?,?,?) on conflict(device_id) do update set received_at=excluded.received_at,snapshot=excluded.snapshot""",
                  (device_id,now,json.dumps(snapshot,ensure_ascii=False)))
        c.commit();c.close()
        applied=0;duplicates=0;state_applied=0;policies_imported=0
        for event in snapshot.get("events_tail",[])[:500]:
            r=self.events.ingest(event)
            if r.get("ok"):
                duplicates+=1 if r.get("duplicate") else 0
                applied+=0 if r.get("duplicate") else 1
        for key,item in (snapshot.get("spine") or {}).items():
            r=self.spine.apply_remote(key,item,device_id)
            if r.get("applied"):state_applied+=1
        c=self.db_factory()
        try:
            for p in snapshot.get("policies",[])[:100]:
                if not p.get("policy_id"):continue
                c.execute("""insert or ignore into behavior_policies(policy_id,created_at,updated_at,scope,trigger_json,action_json,priority,enabled,version,source,rationale,supersedes)
                             values(?,?,?,?,?,?,?,?,?,?,?,?)""",
                          (p["policy_id"],int(p.get("created_at") or now),int(p.get("updated_at") or now),p.get("scope","study"),
                           json.dumps(p.get("trigger") or {},ensure_ascii=False),json.dumps(p.get("action") or {},ensure_ascii=False),
                           int(p.get("priority") or 50),int(bool(p.get("enabled",True))),int(p.get("version") or 1),
                           p.get("source","replica"),p.get("rationale",""),p.get("supersedes","")))
                if c.total_changes:policies_imported+=1
            c.commit()
        finally:c.close()
        return {"ok":True,"received_at":now,"events_applied":applied,"duplicates":duplicates,
                "spine_applied":state_applied,"policies_imported":policies_imported}

    def pull_events(self,after_seq=0,limit=200):
        items=self.events.list_since(after_seq,limit)
        return {"protocol_version":self.protocol_version,"events":items,
                "next_seq":items[-1]["seq"] if items else int(after_seq)}

    def restore_memory_if_empty(self,device_id:str):
        c=self.db_factory();count=c.execute("select count(*) from memory_items where active=1").fetchone()[0]
        row=c.execute("select snapshot from device_snapshots where device_id=?",(device_id,)).fetchone();c.close()
        if count or not row:return {"ok":False,"reason":"server-not-empty-or-no-snapshot"}
        try:s=json.loads(row["snapshot"])
        except Exception:return {"ok":False,"reason":"bad-snapshot"}
        if int(s.get("protocol_version",0))!=self.protocol_version:return {"ok":False,"reason":"protocol-mismatch"}
        restored=0
        for item in s.get("memory",[])[:300]:
            self.memory.upsert(item.get("category","context"),item.get("key","restored"),item.get("value",""),
                               float(item.get("confidence",.5)),"phone-replica")
            restored+=1
        spine_restored=0
        for key,item in (s.get("spine") or {}).items():
            r=self.spine.apply_remote(key,item,device_id)
            if r.get("applied"):spine_restored+=1
        return {"ok":True,"restored_memory":restored,"restored_spine":spine_restored}

    def restore_spine_from_device(self,device_id:str):
        c=self.db_factory();row=c.execute("select snapshot from device_snapshots where device_id=?",(device_id,)).fetchone();c.close()
        if not row:return {"ok":False,"reason":"no-snapshot"}
        try:s=json.loads(row["snapshot"])
        except Exception:return {"ok":False,"reason":"bad-snapshot"}
        if int(s.get("protocol_version",0))!=self.protocol_version:return {"ok":False,"reason":"protocol-mismatch"}
        restored=0
        for key,item in (s.get("spine") or {}).items():
            r=self.spine.apply_remote(key,item,device_id)
            if r.get("applied"):restored+=1
        return {"ok":True,"restored_spine":restored}

    @staticmethod
    def generate_replica_key():
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()

    def write_encrypted_replica(self,path:Path,key:str,payload:dict):
        from cryptography.fernet import Fernet
        dest=Path(path);dest.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode()
        token=Fernet(key.encode()).encrypt(raw)
        tmp=dest.with_suffix(dest.suffix+".tmp");tmp.write_bytes(token);os.replace(tmp,dest)
        return {"ok":True,"path":str(dest),"bytes":len(token)}

    @staticmethod
    def read_encrypted_replica(path:Path,key:str):
        from cryptography.fernet import Fernet
        raw=Fernet(key.encode()).decrypt(Path(path).read_bytes())
        return json.loads(raw.decode())
