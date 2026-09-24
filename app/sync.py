from __future__ import annotations
import json,time

class SyncManager:
    def __init__(self,db_factory,memory,protocol_version=2):
        self.db_factory=db_factory;self.memory=memory;self.protocol_version=int(protocol_version)

    def snapshot(self,current,micro,return_contract,rival,research):
        return {
          "protocol_version":self.protocol_version,
          "server_ts":int(time.time()),
          "session":dict(current),
          "microgoal":micro,
          "return_contract":return_contract,
          "memory":self.memory.relevant(80),
          "rival":rival,
          "research":research[:10]
        }

    def store_offer(self,device_id:str,snapshot:dict):
        now=int(time.time());c=self.db_factory()
        c.execute("""insert into device_snapshots(device_id,received_at,snapshot)
                     values(?,?,?) on conflict(device_id) do update set received_at=excluded.received_at,snapshot=excluded.snapshot""",
                  (device_id,now,json.dumps(snapshot,ensure_ascii=False)))
        c.commit();c.close()
        return {"ok":True,"received_at":now}

    def restore_memory_if_empty(self,device_id:str):
        c=self.db_factory();count=c.execute("select count(*) from memory_items where active=1").fetchone()[0]
        row=c.execute("select snapshot from device_snapshots where device_id=?",(device_id,)).fetchone();c.close()
        if count or not row:return {"ok":False,"reason":"server-not-empty-or-no-snapshot"}
        try:s=json.loads(row["snapshot"])
        except Exception:return {"ok":False,"reason":"bad-snapshot"}
        if int(s.get("protocol_version",0))!=self.protocol_version:return {"ok":False,"reason":"protocol-mismatch"}
        restored=0
        for item in s.get("memory",[])[:200]:
            self.memory.upsert(item.get("category","context"),item.get("key","restored"),item.get("value",""),float(item.get("confidence",.5)),"phone-replica")
            restored+=1
        return {"ok":True,"restored_memory":restored}
