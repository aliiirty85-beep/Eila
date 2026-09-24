from __future__ import annotations

class AttentionFusion:
    STUDY_ZONES={"laptop","screen","monitor","book","tablet"}
    def score(self,gaze:dict|None,desktop:dict|None=None):
        desktop=desktop or {}
        if not gaze:
            return {"score":50.0,"confidence":0.25,"reasons":["no-live-gaze"]}
        zone=(gaze.get("zone") or "unknown").lower()
        ratio=gaze.get("study_ratio_15")
        if ratio is None:ratio=1.0 if zone in self.STUDY_ZONES else (0.0 if zone=="away" else .5)
        ratio=max(0.0,min(1.0,float(ratio)))
        raw=25+70*ratio
        away=float(gaze.get("away_streak_seconds") or 0)
        raw-=min(45,away*4)
        if zone=="away":raw-=12
        elif zone in self.STUDY_ZONES:raw+=5
        quality=max(0.0,min(1.0,float(gaze.get("quality") or .4)))
        # Low-quality gaze should move the verdict toward uncertainty, not toward failure.
        score=50+(raw-50)*(.35+.65*quality)
        if desktop.get("input_recent") is True and zone in {"laptop","screen","monitor"}:score+=2
        score=max(0.0,min(100.0,score))
        confidence=.25+.7*quality
        reasons=[f"zone:{zone}",f"study_ratio:{ratio:.2f}",f"gaze_quality:{quality:.2f}"]
        if away>0:reasons.append(f"away:{away:.1f}s")
        return {"score":round(score,1),"confidence":round(confidence,2),"reasons":reasons}
