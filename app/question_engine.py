from __future__ import annotations
import json

class QuestionEngine:
    def __init__(self,ai,screen,context_registry):
        self.ai=ai
        self.screen=screen
        self.context_registry=context_registry

    async def from_gaze(self,gaze:dict,deep=False):
        zone=(gaze.get("zone") or "").lower()
        active=self.context_registry.current()
        prompt=(
            "یک micro-goal دقیق فارسی بساز. فقط از محتوای قابل مشاهده/داده‌شده استفاده کن. "
            "اگر تست مشخص است همان تست؛ اگر متن است یک قطعه کوچک. یک خروجی قابل تحویل لازم است. "
            "Gaze فقط سرنخ زمان‌بندی است و نباید از آن حالت ذهنی قطعی استنباط کنی. "
            "اگر gaze نشان می‌دهد مکث طولانی/بازگشت/پرش وجود دارد، سؤال علت‌ومعلولی یا دام مفهومی بساز. "
            "فقط JSON بده: "
            "{\"study\":true,\"kind\":\"test|read|problem|recall\",\"instruction\":\"...\","
            "\"question\":\"...\",\"expected\":\"\",\"seconds\":60,\"topic\":\"...\","
            "\"hook\":\"...\",\"confidence\":0.8}"
        )
        content=[{
            "type":"text",
            "text":prompt+"\nGaze summary: "+json.dumps(gaze,ensure_ascii=False)
        }]
        if active and active.get("content"):
            content.append({
                "type":"text",
                "text":"Active source context:\n"+active["content"][:12000]
            })

        shot=None
        if zone in ("laptop","screen","monitor","unknown",""):
            shot=self.screen.capture_jpeg()
            if shot:
                content.append({
                    "type":"image_url",
                    "image_url":{"url":self.screen.data_url(shot)}
                })
                x,y=gaze.get("x"),gaze.get("y")
                if x is not None and y is not None:
                    crop=self.screen.crop_from_normalized(shot,x,y)
                    if crop:
                        content.append({
                            "type":"image_url",
                            "image_url":{"url":self.screen.data_url(crop)}
                        })

        tier="deep" if deep and not shot else ("vision" if shot else "deep")
        result=await self.ai.ask_json(
            tier,
            [{"role":"user","content":content}],
            max_tokens=850
        )
        if not result.get("ok"):
            return result

        d=result["data"]
        if not d.get("study",True):
            return {"ok":False,"error":"not-study","raw":result.get("raw","")}
        d["seconds"]=max(20,min(180,int(d.get("seconds") or 60)))
        return {"ok":True,"data":d}
