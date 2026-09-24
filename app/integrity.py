from __future__ import annotations

class StudyIntegrity:
    def assess(self,attention_score:float,gaze:dict|None,screen_change:float|None,input_recent:bool|None,pulse:dict|None):
        gaze=gaze or {}; pulse=pulse or {}; flags=[]; suspicion=0.0
        if input_recent and attention_score<40: suspicion+=.25; flags.append("input-with-low-attention")
        if screen_change is not None and screen_change>.25 and float(gaze.get("study_ratio_15") or 1)<.45:
            suspicion+=.25; flags.append("screen-activity-with-low-study-gaze")
        if pulse.get("attempts",0)>=3 and pulse.get("score",100)<40: suspicion+=.25; flags.append("activity-with-weak-learning-evidence")
        if float(gaze.get("jump_rate") or 0)>.5: suspicion+=.15; flags.append("unstable-gaze")
        return {"suspicion":round(min(1.0,suspicion),2),"flags":flags,"label":"suspicious" if suspicion>=.5 else ("uncertain" if suspicion>=.25 else "normal")}
