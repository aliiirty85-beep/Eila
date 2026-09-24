from __future__ import annotations
import time, json

class DeviceHub:
    def __init__(self,db_factory,stale_seconds=15):
        self.db_factory=db_factory; self.stale_seconds=int(stale_seconds); self.live={}

    def heartbeat(self,device_id:str,kind="unknown",name="",capabilities=None,state=None):
        now=int(time.time())
        payload={"device_id":device_id,"kind":kind,"name":name,"last_seen":now,"capabilities":capabilities or {},"state":state or {}}
        self.live[device_id]=payload
        c=self.db_factory()
        c.execute("""insert into devices(device_id,kind,name,last_seen,capabilities,state) values(?,?,?,?,?,?)
                     on conflict(device_id) do update set kind=excluded.kind,name=excluded.name,last_seen=excluded.last_seen,
                     capabilities=excluded.capabilities,state=excluded.state""",
                  (device_id,kind,name,now,json.dumps(capabilities or {},ensure_ascii=False),json.dumps(state or {},ensure_ascii=False)))
        c.commit(); c.close(); return payload

    def ingest_gaze(self,device_id:str,sample:dict):
        d=self.live.get(device_id) or self.heartbeat(device_id,kind="android")
        d["last_seen"]=int(time.time()); d["gaze"]=dict(sample); return d

    def devices(self):
        now=time.time(); out=[]
        for d in self.live.values():
            x=dict(d); x["stale"]=now-x.get("last_seen",0)>self.stale_seconds; out.append(x)
        return out

    def primary_gaze(self):
        now=time.time(); candidates=[]
        for d in self.live.values():
            g=d.get("gaze")
            if not g: continue
            age=now-d.get("last_seen",0)
            if age>self.stale_seconds: continue
            quality=float(g.get("quality",0.5) or 0.5)
            candidates.append((quality-age*0.02,d["device_id"],g))
        if not candidates: return None,None
        candidates.sort(reverse=True); _,did,g=candidates[0]; return did,g
