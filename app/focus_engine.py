from __future__ import annotations
import time
from collections import deque

class FocusEngine:
    def __init__(self,cfg:dict):
        self.cfg=cfg; self.scores=deque(maxlen=30); self.interventions=deque(maxlen=30); self.session_started=time.time()

    def observe(self,score:float): self.scores.append((time.time(),float(score)))

    def phase(self,score:float):
        elapsed=time.time()-self.session_started
        if elapsed<180: return "RAMP"
        if score>=82 and elapsed>=480: return "FLOW"
        if score>=65: return "LOCK"
        return "RECOVER"

    def risk(self,score:float,gaze:dict|None,micro:dict|None):
        gaze=gaze or {}; risk=0.0; reasons=[]; vals=[s for _,s in self.scores]
        if len(vals)>=4:
            slope=(vals[-1]-vals[-4])/3
            if slope<-5: risk+=.30; reasons.append("attention-falling")
        away=float(gaze.get("away_streak_seconds") or 0)
        if away>=3: risk+=min(.35,away/20); reasons.append("away-building")
        jr=gaze.get("jump_rate")
        if jr is not None and float(jr)>.32: risk+=.20; reasons.append("gaze-jumpy")
        fix=float(gaze.get("max_fixation_seconds") or 0)
        if jr is not None and float(jr)>.38 and fix<.8: risk+=.20; reasons.append("low-dwell")
        if micro and micro.get("remaining_seconds",999)<15: risk+=.10; reasons.append("deadline-near")
        if score<55: risk+=.25; reasons.append("low-score")
        risk=min(1.0,risk)
        return {"risk":round(risk,2),"level":"high" if risk>=.65 else ("medium" if risk>=.35 else "low"),"reasons":reasons}

    def flow_protected(self,score:float,gaze:dict|None,micro:dict|None):
        if not micro: return False
        gaze=gaze or {}; ratio=gaze.get("study_ratio_15"); away=float(gaze.get("away_streak_seconds") or 0)
        threshold=float(self.cfg.get("flow_protection_min_attention",78))
        return score>=threshold and (ratio is None or float(ratio)>=.75) and away<2

    def can_intervene(self,critical=False):
        if critical: return True
        now=time.time()
        while self.interventions and now-self.interventions[0]>300: self.interventions.popleft()
        return len(self.interventions)<int(self.cfg.get("intervention_budget_per_5min",4))

    def mark_intervention(self): self.interventions.append(time.time())
