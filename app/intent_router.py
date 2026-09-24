from __future__ import annotations
import re

FA_DIGITS=str.maketrans("۰۱۲۳۴۵۶۷۸۹","0123456789")
WORDS={"یک":1,"دو":2,"سه":3,"چهار":4,"پنج":5,"شش":6,"هفت":7,"هشت":8,"نه":9,"ده":10,"پانزده":15,"بیست":20,"سی":30,"چهل":40,"شصت":60}

class IntentRouter:
    def _minutes(self,text:str):
        t=text.translate(FA_DIGITS).lower()
        m=re.search(r"(\d+(?:\.\d+)?)\s*(?:دقیقه|min|minutes?)",t)
        if m:return float(m.group(1))
        for w,n in WORDS.items():
            if re.search(rf"\b{re.escape(w)}\s*دقیقه",t):return float(n)
        return None

    def local(self,text:str):
        t=(text or "").strip().lower()
        if re.search(r"(برگشتم|رسیدم|اومدم|آمدم)\b",t):
            return {"intent":"return_ack"}
        mins=self._minutes(t)
        leaving=bool(re.search(r"(می.?رم|میرم|برمی.?گردم|برمیگردم|میام|می.?آم|تا .* برگرد)",t))
        if mins is not None and leaving:
            return {"intent":"return_contract","minutes":mins,"text":text.strip()}
        return {"intent":"unknown"}

    async def classify_focus(self,ai,text:str,current_goal:str,micro:dict|None):
        prompt=(
          "پیام کاربر را برای Focus Mode فقط به یکی از این برچسب‌ها طبقه‌بندی کن: "
          "study_related, urgent_life_health, unrelated. "
          "اگر سؤال درباره همان درس، پاسخ micro-goal، ابزار ضروری مطالعه، یا مشکل فوری سلامت/زندگی است block نکن. "
          "اگر صرفاً گفت‌وگوی حاشیه‌ای است unrelated. فقط JSON {\"label\":\"...\",\"confidence\":0.0}.\n"
          f"هدف: {current_goal}\nMicro: {micro}\nپیام: {text}"
        )
        r=await ai.ask_json("fast",[{"role":"user","content":prompt}],max_tokens=120)
        if not r.get("ok"):return {"label":"study_related","confidence":0.0,"fallback":True}
        d=r["data"];return {"label":d.get("label","study_related"),"confidence":float(d.get("confidence") or 0)}
