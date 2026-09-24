from __future__ import annotations
import time,json,uuid

ALLOWED={"mastery","error","behavior","decision","context","commitment","preference"}
SAFE_ACTION_PREFIXES=("microgoal.","intervention.","novelty.","competition.","flow.","voice.","review.","return.","firewall.")

class MemoryManager:
    def __init__(self,db_factory): self.db_factory=db_factory
    def upsert(self,category,key,value,confidence=.6,source=""):
        category=category if category in ALLOWED else "context";now=int(time.time());c=self.db_factory()
        c.execute("""insert into memory_items(created_at,updated_at,category,key,value,confidence,source,active)
                     values(?,?,?,?,?,?,?,1)
                     on conflict(category,key) do update set updated_at=excluded.updated_at,value=excluded.value,
                     confidence=excluded.confidence,source=excluded.source,active=1""",
                  (now,now,category,key,value,float(confidence),source))
        c.commit();c.close()
    def relevant(self,limit=40):
        c=self.db_factory();rows=c.execute("""select category,key,value,confidence,updated_at from memory_items
          where active=1 order by confidence desc,updated_at desc limit ?""",(int(limit),)).fetchall();c.close()
        return [dict(r) for r in rows]
    def session_summary(self,session_id):
        c=self.db_factory();ev=c.execute("select kind,passed,topic,error_type from learning_evidence where session_id=? order by id",(session_id,)).fetchall();c.close()
        if not ev:return {"text":"شواهد یادگیری کافی ثبت نشد.","points":[]}
        passed=sum(1 for r in ev if r["passed"]);attempts=len(ev);errors={}
        for r in ev:
            if r["error_type"]:errors[r["error_type"]]=errors.get(r["error_type"],0)+1
        best=max(errors,key=errors.get) if errors else "";points=[f"{passed}/{attempts} شواهد یادگیری تأیید شد."]
        if best:points.append(f"پرتکرارترین نوع خطا: {best}.")
        return {"text":" ".join(points),"points":points}


class PolicyEngine:
    """Versioned live behavior rules. Safe rules hot-reload; capability changes become requests."""
    def __init__(self,db_factory,event_bus=None):
        self.db_factory=db_factory;self.events=event_bus

    def add(self,scope:str,trigger:dict,action:dict,priority=50,source="user",rationale="",policy_id=None,supersedes=""):
        if not self._safe_action(action):return {"ok":False,"reason":"capability-level-or-unsafe-action"}
        pid=policy_id or str(uuid.uuid4());now=int(time.time());c=self.db_factory()
        old=c.execute("select version,created_at from behavior_policies where policy_id=?",(pid,)).fetchone()
        version=int(old["version"])+1 if old else 1;created=int(old["created_at"]) if old else now
        c.execute("""insert into behavior_policies(policy_id,created_at,updated_at,scope,trigger_json,action_json,priority,enabled,version,source,rationale,supersedes)
                     values(?,?,?,?,?,?,?,?,?,?,?,?)
                     on conflict(policy_id) do update set updated_at=excluded.updated_at,scope=excluded.scope,
                     trigger_json=excluded.trigger_json,action_json=excluded.action_json,priority=excluded.priority,
                     enabled=excluded.enabled,version=excluded.version,source=excluded.source,
                     rationale=excluded.rationale,supersedes=excluded.supersedes""",
                  (pid,created,now,scope,json.dumps(trigger,ensure_ascii=False),json.dumps(action,ensure_ascii=False),
                   int(priority),1,version,source,rationale,supersedes))
        c.commit();c.close()
        if self.events:self.events.emit("policy.changed",{"policy_id":pid,"scope":scope,"trigger":trigger,"action":action,"priority":priority},source,pid,version)
        return {"ok":True,"policy":self.get(pid)}

    def disable(self,policy_id:str,source="user"):
        now=int(time.time());c=self.db_factory();r=c.execute("select version from behavior_policies where policy_id=?",(policy_id,)).fetchone()
        if not r:c.close();return {"ok":False,"reason":"not-found"}
        version=int(r["version"])+1
        c.execute("update behavior_policies set enabled=0,updated_at=?,version=? where policy_id=?",(now,version,policy_id));c.commit();c.close()
        if self.events:self.events.emit("policy.disabled",{"policy_id":policy_id},source,policy_id,version)
        return {"ok":True,"policy":self.get(policy_id)}

    def get(self,policy_id):
        c=self.db_factory();r=c.execute("select * from behavior_policies where policy_id=?",(policy_id,)).fetchone();c.close()
        return self._row(r) if r else None

    def list(self,enabled_only=True):
        c=self.db_factory()
        rows=c.execute("select * from behavior_policies where enabled=1 order by priority desc,updated_at desc").fetchall() if enabled_only else c.execute("select * from behavior_policies order by updated_at desc").fetchall()
        c.close();return [self._row(r) for r in rows]

    def resolve(self,context:dict,scope="study"):
        return [p for p in self.list(True) if p["scope"] in (scope,"global","*") and self._matches(p["trigger"],context)]

    @staticmethod
    def _safe_action(action):
        if not isinstance(action,dict) or not action:return False
        return all(any(str(k).startswith(prefix) for prefix in SAFE_ACTION_PREFIXES) for k in action)

    @staticmethod
    def _matches(trigger,context):
        for k,v in (trigger or {}).items():
            actual=context.get(k)
            if isinstance(v,dict):
                if "min" in v and (actual is None or float(actual)<float(v["min"])):return False
                if "max" in v and (actual is None or float(actual)>float(v["max"])):return False
                if "in" in v and actual not in v["in"]:return False
            elif actual!=v:return False
        return True

    @staticmethod
    def _row(r):
        d=dict(r)
        try:d["trigger"]=json.loads(d.pop("trigger_json"))
        except Exception:d["trigger"]={}
        try:d["action"]=json.loads(d.pop("action_json"))
        except Exception:d["action"]={}
        d["enabled"]=bool(d["enabled"]);return d


class EvolutionEngine:
    """Turns a natural-language 'from now on' request into a policy or capability request."""
    def __init__(self,db_factory,ai,policies:PolicyEngine):
        self.db_factory=db_factory;self.ai=ai;self.policies=policies

    async def apply_request(self,text:str):
        prompt=(
          "درخواست کاربر برای تغییر رفتار ایلا را ساختاری کن. اگر فقط تغییر رفتار/تنظیم است kind=policy. "
          "اگر نیاز به سنسور، permission، API یا کد جدید دارد kind=capability. "
          "برای policy فقط action keyهای مجاز: microgoal.*, intervention.*, novelty.*, competition.*, flow.*, voice.*, review.*, return.*, firewall.*. "
          "فقط JSON: {"kind":"policy|capability","scope":"study|global","trigger":{},"action":{},"
          ""priority":50,"rationale":"...","capability_spec":{}}. متن: "+text
        )
        r=await self.ai.ask_json("deep",[{"role":"user","content":prompt}],max_tokens=500)
        if not r.get("ok"):return {"ok":False,"reason":"ai-unavailable","detail":r.get("error")}
        d=r["data"]
        if d.get("kind")=="policy":
            out=self.policies.add(d.get("scope","study"),d.get("trigger") or {},d.get("action") or {},
                                  d.get("priority",50),"user",d.get("rationale",""))
            out["kind"]="policy";return out
        rid=str(uuid.uuid4());c=self.db_factory()
        c.execute("insert into capability_requests(request_id,created_at,request_text,spec,status,source) values(?,?,?,?,?,?)",
                  (rid,int(time.time()),text,json.dumps(d.get("capability_spec") or {},ensure_ascii=False),"proposed","user"))
        c.commit();c.close()
        return {"ok":True,"kind":"capability","request_id":rid,"spec":d.get("capability_spec") or {}}

    def capability_requests(self,limit=30):
        c=self.db_factory();rows=c.execute("select * from capability_requests order by created_at desc limit ?",(int(limit),)).fetchall();c.close()
        out=[]
        for r in rows:
            d=dict(r)
            try:d["spec"]=json.loads(d["spec"])
            except Exception:d["spec"]={}
            out.append(d)
        return out
