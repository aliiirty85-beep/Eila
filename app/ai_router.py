from __future__ import annotations
import os, time
from dotenv import load_dotenv
load_dotenv()

class AIRouter:
    def __init__(self, cfg:dict):
        self.cfg=cfg.get("ai",{})
        self.failures={}
        self.blocked_until={}

    def _models(self,tier:str):
        env=self.cfg.get(f"{tier}_models_env","")
        raw=os.getenv(env,"") if env else ""
        models=[x.strip() for x in raw.split(",") if x.strip()]
        for m in self.cfg.get("fallback_models",[]):
            if m not in models: models.append(m)
        return models

    def _available(self, model:str):
        return time.time() >= self.blocked_until.get(model,0)

    def _fail(self, model:str):
        n=self.failures.get(model,0)+1
        self.failures[model]=n
        if n>=3:
            self.blocked_until[model]=time.time()+min(300,30*n)

    def _ok(self, model:str):
        self.failures[model]=0
        self.blocked_until[model]=0

    async def ask(self,tier:str,messages:list[dict],temperature=.2,max_tokens=700):
        try:
            from litellm import acompletion
        except Exception as e:
            return f"__AI_ERROR__:litellm:{type(e).__name__}"
        errors=[]
        for model in self._models(tier):
            if not self._available(model): continue
            try:
                r=await acompletion(model=model,messages=messages,temperature=temperature,max_tokens=max_tokens,timeout=45)
                self._ok(model)
                return (r.choices[0].message.content or "").strip()
            except Exception as e:
                self._fail(model)
                errors.append(f"{model}:{type(e).__name__}")
        return "__AI_ERROR__:"+" | ".join(errors or ["no-model"])

    def health(self):
        return {
          "models":{tier:self._models(tier) for tier in ("fast","deep","vision","judge","research")},
          "blocked_until":self.blocked_until
        }
