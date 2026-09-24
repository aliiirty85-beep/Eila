from __future__ import annotations
import json, time

class CommandBus:
    def __init__(self,db_factory): self.db_factory=db_factory
    def queue(self,kind:str,payload:dict,target_device="*",ttl_seconds=600):
        now=int(time.time()); c=self.db_factory()
        cur=c.execute("insert into device_commands(created_at,expires_at,target_device,kind,payload) values(?,?,?,?,?)",(now,now+int(ttl_seconds),target_device,kind,json.dumps(payload,ensure_ascii=False)))
        c.commit(); cid=int(cur.lastrowid); c.close(); return cid
    def pending(self,device_id:str):
        now=int(time.time()); c=self.db_factory()
        rows=c.execute("""select d.* from device_commands d where (d.expires_at is null or d.expires_at>=?)
          and (d.target_device='*' or d.target_device=?)
          and not exists(select 1 from command_acks a where a.command_id=d.id and a.device_id=?)
          order by d.id asc limit 50""",(now,device_id,device_id)).fetchall(); c.close()
        out=[]
        for r in rows:
            d=dict(r)
            try:d["payload"]=json.loads(d["payload"])
            except Exception:d["payload"]={}
            out.append(d)
        return out
    def ack(self,command_id:int,device_id:str):
        c=self.db_factory(); c.execute("insert or replace into command_acks(command_id,device_id,acked_at) values(?,?,?)",(int(command_id),device_id,int(time.time()))); c.commit(); c.close()
