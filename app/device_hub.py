from __future__ import annotations
import time,json

class DeviceHub:
    def __init__(self,db_factory,stale_seconds=15,event_bus=None):
        self.db_factory=db_factory;self.stale_seconds=int(stale_seconds);self.live={};self.events=event_bus

    def heartbeat(self,device_id:str,kind="unknown",name="",capabilities=None,state=None,hardware_fingerprint=""):
        now=int(time.time());cap=capabilities or {};st=state or {}
        existing=self.get(device_id)
        joined=int(existing.get("joined_at") or 0) if existing else now
        rev=int(existing.get("device_revision") or 0)+1 if existing else 1
        payload={"device_id":device_id,"kind":kind,"name":name,"last_seen":now,
                 "capabilities":cap,"state":st,"status":"active",
                 "hardware_fingerprint":hardware_fingerprint or (existing or {}).get("hardware_fingerprint",""),
                 "joined_at":joined,"device_revision":rev}
        self.live[device_id]=payload
        c=self.db_factory()
        c.execute("""insert into devices(device_id,kind,name,last_seen,capabilities,state,joined_at,status,hardware_fingerprint,device_revision)
                     values(?,?,?,?,?,?,?,?,?,?)
                     on conflict(device_id) do update set kind=excluded.kind,name=excluded.name,last_seen=excluded.last_seen,
                     capabilities=excluded.capabilities,state=excluded.state,status='active',
                     hardware_fingerprint=case when excluded.hardware_fingerprint='' then devices.hardware_fingerprint else excluded.hardware_fingerprint end,
                     device_revision=excluded.device_revision""",
                  (device_id,kind,name,now,json.dumps(cap,ensure_ascii=False),json.dumps(st,ensure_ascii=False),
                   joined,"active",payload["hardware_fingerprint"],rev))
        c.commit();c.close()
        if self.events:self.events.emit("device.heartbeat",{"kind":kind,"name":name,"capabilities":cap},device_id,device_id,rev)
        return payload

    def ingest_gaze(self,device_id:str,sample:dict):
        d=self.live.get(device_id) or self.heartbeat(device_id,kind="android")
        d["last_seen"]=int(time.time());d["gaze"]=dict(sample);return d

    def get(self,device_id:str):
        if device_id in self.live:return dict(self.live[device_id])
        c=self.db_factory();r=c.execute("select * from devices where device_id=?",(device_id,)).fetchone();c.close()
        return self._decode(r) if r else None

    def devices(self,include_retired=False):
        now=time.time();out=[]
        seen=set()
        for d in self.live.values():
            x=dict(d);x["stale"]=now-x.get("last_seen",0)>self.stale_seconds;out.append(x);seen.add(x["device_id"])
        c=self.db_factory()
        rows=c.execute("select * from devices").fetchall();c.close()
        for r in rows:
            x=self._decode(r)
            if x["device_id"] in seen:continue
            if not include_retired and x.get("status")=="retired":continue
            x["stale"]=now-float(x.get("last_seen") or 0)>self.stale_seconds;out.append(x)
        return out

    def retire(self,device_id:str,reason="replaced"):
        now=int(time.time());c=self.db_factory();r=c.execute("select device_revision from devices where device_id=?",(device_id,)).fetchone()
        if not r:c.close();return {"ok":False,"reason":"not-found"}
        rev=int(r["device_revision"] or 0)+1
        c.execute("update devices set status='retired',retired_at=?,device_revision=? where device_id=?",(now,rev,device_id));c.commit();c.close()
        self.live.pop(device_id,None)
        if self.events:self.events.emit("device.retired",{"reason":reason},device_id,device_id,rev)
        return {"ok":True,"device":self.get(device_id)}

    def replace(self,old_device_id:str,new_device_id:str,kind="laptop",name="",capabilities=None,hardware_fingerprint=""):
        old=self.get(old_device_id)
        new=self.heartbeat(new_device_id,kind,name,capabilities or {},{},hardware_fingerprint)
        retired=self.retire(old_device_id,"replaced-by:"+new_device_id)
        rec=[]
        if not old or old.get("hardware_fingerprint")!=new.get("hardware_fingerprint"):
            rec=["gaze-screen-geometry","camera-geometry"]
        return {"ok":True,"old":retired,"new":new,"requires_recalibration":rec}

    def capability_report(self):
        report=[]
        for d in self.devices():
            for name,value in (d.get("capabilities") or {}).items():
                if value:
                    report.append({"capability":name,"provider_device":d["device_id"],
                                   "status":"stale" if d.get("stale") else "online"})
        return report

    def primary_gaze(self):
        now=time.time();candidates=[]
        for d in self.live.values():
            g=d.get("gaze")
            if not g:continue
            age=now-d.get("last_seen",0)
            if age>self.stale_seconds:continue
            quality=float(g.get("quality",0.5) or 0.5)
            candidates.append((quality-age*0.02,d["device_id"],g))
        if not candidates:return None,None
        candidates.sort(reverse=True);_,did,g=candidates[0];return did,g

    @staticmethod
    def _decode(r):
        d=dict(r)
        for k in ("capabilities","state"):
            try:d[k]=json.loads(d.get(k) or "{}")
            except Exception:d[k]={}
        return d
