from __future__ import annotations
import json,re,time

class ContextVerifier:
    """Probabilistic reality checks. Never labels the user a liar.

    Driving is safety-sensitive: probable driving suppresses visual study pressure.
    Eating is intrinsically hard to verify passively without intrusive sensors.
    Sleeping uses only weak passive evidence unless a trusted wearable/source is added.
    """
    def __init__(self,db_factory,cfg:dict):
        self.db_factory=db_factory
        self.defaults=cfg.get("activity_claim_defaults_minutes",{})

    def parse_claim(self,text:str):
        t=(text or "").strip().lower()
        patterns={
          "driving":r"(رانندگی|پشت فرمون|پشت فرمان|دارم می.?رونم)",
          "eating":r"(غذا می.?خور|ناهار|شام|صبحانه|دارم می.?خورم)",
          "sleeping":r"(می.?خوابم|میخوابم|خوابیدن|برم بخواب|دارم می.?خوابم)",
          "resting":r"(استراحت|ریلکس)"
        }
        for activity,p in patterns.items():
            if re.search(p,t):return activity
        return None

    def claim(self,activity:str,minutes:float|None=None,note:str="",source="user"):
        activity=activity.strip().lower()
        now=int(time.time())
        if minutes is None:minutes=float(self.defaults.get(activity,30))
        until=now+max(60,int(float(minutes)*60))
        c=self.db_factory()
        cur=c.execute("""insert into context_claims(created_at,activity,claimed_until,source,status,details)
                         values(?,?,?,?,?,?)""",(now,activity,until,source,"active",json.dumps({"note":note},ensure_ascii=False)))
        c.commit();cid=int(cur.lastrowid);c.close()
        return self.evaluate(cid)

    def evidence(self,device_id:str,facts:dict,kind="device"):
        now=int(time.time());c=self.db_factory()
        c.execute("insert into context_evidence(ts,device_id,kind,payload) values(?,?,?,?)",
                  (now,device_id,kind,json.dumps(facts,ensure_ascii=False)))
        c.commit();c.close()
        active=self.status()
        if active and active.get("id"):return self.evaluate(active["id"])
        return {"ok":True,"active":False}

    def _recent_facts(self,seconds=900):
        c=self.db_factory()
        rows=c.execute("select * from context_evidence where ts>=? order by id desc limit 60",(int(time.time())-seconds,)).fetchall()
        devices=c.execute("select device_id,last_seen,state from devices where last_seen>=? order by last_seen desc",(int(time.time())-seconds,)).fetchall()
        c.close()
        out=[]
        for r in rows:
            try:p=json.loads(r["payload"])
            except Exception:p={}
            out.append({"device_id":r["device_id"],"kind":r["kind"],**p})
        for d in devices:
            try:p=json.loads(d["state"])
            except Exception:p={}
            out.append({"device_id":d["device_id"],"kind":"heartbeat",**p})
        return out

    def _score(self,activity:str,facts:list[dict]):
        score=.28
        reasons=["user-claim"]
        flat={}
        for f in facts:
            for k,v in f.items():
                if k not in ("device_id","kind") and v is not None:flat[k]=v

        if activity=="driving":
            if str(flat.get("activity","")).lower() in {"in_vehicle","driving","vehicle"}:
                score=max(score,.88);reasons.append("activity-recognition:vehicle")
            try:
                speed=float(flat.get("speed_mps",0) or 0)
                if speed>=8:score=max(score,.93);reasons.append("speed>=8m/s")
                elif speed>=3:score=max(score,.72);reasons.append("speed>=3m/s")
            except Exception:pass
            if flat.get("car_bluetooth") is True:
                score=max(score,.70);reasons.append("car-bluetooth")
            verdict="probable" if score>=.65 else "uncertain"
            return score,verdict,reasons,True

        if activity=="sleeping":
            interactive=flat.get("screen_interactive")
            face_age=flat.get("face_seen_seconds_ago")
            no_motion=flat.get("no_motion_minutes")
            if interactive is False:
                score+=.18;reasons.append("screen-off")
            try:
                if float(face_age or 0)>=300:score+=.14;reasons.append("no-face>=5m")
            except Exception:pass
            try:
                if float(no_motion or 0)>=20:score+=.25;reasons.append("no-motion>=20m")
            except Exception:pass
            if flat.get("wearable_sleep") is True:
                score=max(score,.90);reasons.append("wearable-sleep")
            score=min(.96,score)
            verdict="probable" if score>=.65 else "uncertain"
            return score,verdict,reasons,True

        if activity=="eating":
            # Passive phone signals cannot reliably prove eating.
            if flat.get("meal_one_shot_confirmed") is True:
                score=max(score,.82);reasons.append("one-shot-meal-evidence")
            if flat.get("wearable_meal_event") is True:
                score=max(score,.75);reasons.append("trusted-meal-event")
            verdict="probable" if score>=.65 else "uncertain"
            return score,verdict,reasons,True

        if activity=="resting":
            if flat.get("screen_interactive") is False:
                score+=.15;reasons.append("screen-off")
            return min(.8,score),"probable" if score>=.55 else "uncertain",reasons,True

        return score,"uncertain",reasons,False

    def evaluate(self,claim_id:int):
        c=self.db_factory();r=c.execute("select * from context_claims where id=?",(int(claim_id),)).fetchone();c.close()
        if not r:return {"ok":False,"reason":"claim-not-found"}
        d=dict(r)
        if d.get("claimed_until") and int(d["claimed_until"])<int(time.time()):
            c=self.db_factory();c.execute("update context_claims set status='expired' where id=?",(claim_id,));c.commit();c.close()
            return {"ok":True,"active":False,"id":claim_id,"activity":d["activity"],"verdict":"expired","confidence":0}
        score,verdict,reasons,blocks=self._score(d["activity"],self._recent_facts())
        c=self.db_factory();c.execute("update context_claims set confidence=?,verdict=?,details=? where id=?",
          (float(score),verdict,json.dumps({"reasons":reasons,"blocks_study":blocks},ensure_ascii=False),claim_id));c.commit();c.close()
        return {"ok":True,"active":True,"id":claim_id,"activity":d["activity"],"claimed_until":d["claimed_until"],
                "confidence":round(score,2),"verdict":verdict,"reasons":reasons,
                "blocks_study":bool(blocks),"safety_mode":"driving" if d["activity"]=="driving" and score>=.35 else ""}

    def status(self):
        c=self.db_factory();r=c.execute("""select id from context_claims where status='active'
                                          and (claimed_until is null or claimed_until>=?)
                                          order by id desc limit 1""",(int(time.time()),)).fetchone();c.close()
        return self.evaluate(int(r["id"])) if r else None

    def finish(self):
        c=self.db_factory();c.execute("update context_claims set status='done' where status='active'");c.commit();c.close()
        return {"ok":True}
