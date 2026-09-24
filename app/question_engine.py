from __future__ import annotations
import json

class QuestionEngine:
    def __init__(self,ai,screen,context_registry):
        self.ai=ai;self.screen=screen;self.context_registry=context_registry

    async def from_gaze(self,gaze:dict,deep=False):
        zone=(gaze.get("zone") or "").lower();active=self.context_registry.current()
        prompt=(
            "یک micro-goal دقیق فارسی بساز. فقط از محتوای قابل مشاهده/داده‌شده استفاده کن. "
            "اگر تست مشخص است همان تست؛ اگر متن است یک قطعه کوچک. یک خروجی قابل تحویل لازم است. "
            "Gaze فقط سرنخ زمان‌بندی است و نباید از آن حالت ذهنی قطعی استنباط کنی. "
            "اگر مکث طولانی/بازگشت/پرش دیده شده، سؤال علت‌ومعلولی، دام مفهومی یا teach-back مرتبط بساز. "
            "فقط JSON: {\"study\":true,\"kind\":\"test|read|problem|recall\",\"instruction\":\"...\","
            "\"question\":\"...\",\"expected\":\"\",\"seconds\":60,\"topic\":\"...\",\"hook\":\"...\",\"confidence\":0.8}"
        )
        content=[{"type":"text","text":prompt+"\nGaze summary: "+json.dumps(gaze,ensure_ascii=False)}]
        has_source=False
        has_image_source=False
        if active and active.get("content"):
            has_source=True
            content.append({"type":"text","text":"Active source context:\n"+active["content"][:12000]})
        if active and active.get("kind")=="image" and active.get("ref"):
            try:
                from pathlib import Path
                page=Path(active["ref"]).read_bytes()
                if page:
                    has_source=True
                    has_image_source=True
                    content.append({"type":"image_url","image_url":{"url":self.screen.data_url(page)}})
            except Exception:
                pass
        shot=None
        if zone in ("laptop","screen","monitor","unknown",""):
            shot=self.screen.capture_jpeg()
            if shot:
                content.append({"type":"image_url","image_url":{"url":self.screen.data_url(shot)}})
                x,y=gaze.get("x"),gaze.get("y")
                if x is not None and y is not None:
                    crop=self.screen.crop_from_normalized(shot,x,y)
                    if crop:content.append({"type":"image_url","image_url":{"url":self.screen.data_url(crop)}})
        if not shot and not has_source:
            return {"ok":False,"error":"content-required","detail":"برای کتاب/صفحه غیرقابل‌مشاهده باید source context یا snapshot داشته باشم."}
        tier="vision" if (shot or has_image_source) else "deep"
        result=await self.ai.ask_json(tier,[{"role":"user","content":content}],max_tokens=850)
        if not result.get("ok"):return result
        d=result["data"]
        if not d.get("study",True):return {"ok":False,"error":"not-study","raw":result.get("raw","")}
        d["seconds"]=max(20,min(180,int(d.get("seconds") or 60)))
        return {"ok":True,"data":d}


    async def repair_after_failure(self,finished:dict,answer:str,error_type:str="",topic:str=""):
        active=self.context_registry.current()
        prompt=(
            "برای یک پاسخ غلط، یک repair micro-goal بسیار کوچک فارسی بساز؛ هدف توضیح خطاست نه تنبیه. "
            "بعد از repair یک retest متفاوت ولی هم‌مفهوم لازم است. اگر منبع کافی نیست، از حدس درباره محتوای دیده‌نشده خودداری کن. "
            'فقط JSON: {"ok":true,"repair_instruction":"...","repair_question":"...","repair_expected":"",'
            '"repair_seconds":35,"retest_instruction":"...","retest_question":"...","retest_expected":"",'
            '"retest_seconds":55,"topic":"...","error_type":"concept-gap|inattention|rushing|calculation|option-reading|forgetting|unknown"}.'
        )
        payload={
            "kind":finished.get("kind","study"),
            "instruction":finished.get("instruction",""),
            "question":finished.get("question",""),
            "user_answer":answer,
            "reported_error_type":error_type,
            "topic":topic or finished.get("context_ref","")
        }
        content=[{"type":"text","text":prompt+"\nAttempt:\n"+json.dumps(payload,ensure_ascii=False)}]
        has_source=False
        if active and active.get("content"):
            has_source=True;content.append({"type":"text","text":"Active source context:\n"+active["content"][:12000]})
        if active and active.get("kind")=="image" and active.get("ref"):
            try:
                from pathlib import Path
                page=Path(active["ref"]).read_bytes()
                if page:
                    has_source=True
                    content.append({"type":"image_url","image_url":{"url":self.screen.data_url(page)}})
            except Exception:
                pass
        if not has_source and not finished.get("question") and not finished.get("instruction"):
            return {"ok":False,"error":"insufficient-context"}
        tier="vision" if active and active.get("kind")=="image" else "deep"
        r=await self.ai.ask_json(tier,[{"role":"user","content":content}],max_tokens=750)
        if not r.get("ok"):return r
        d=r["data"]
        d["repair_seconds"]=max(20,min(90,int(d.get("repair_seconds") or 35)))
        d["retest_seconds"]=max(20,min(120,int(d.get("retest_seconds") or 55)))
        return {"ok":True,"data":d}
