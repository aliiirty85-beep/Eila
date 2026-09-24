from __future__ import annotations
import hashlib, math, time
from collections import deque
from datetime import date

STYLES=("duel","mystery","boss","precision","sprint","teachback","streak","comeback")
THEMES=("رقابت","کنجکاوی","دقت","شکار خطا","بازگشت سریع","توضیح دادن","رکورد شخصی","آرامش عمیق")

class EngagementEngine:
    def __init__(self,db_factory):
        self.db_factory=db_factory
        self.last_styles=deque(maxlen=3)
        self.interventions=deque(maxlen=20)
        self.session_started=time.time()

    @property
    def daily_theme(self):
        h=hashlib.sha256(date.today().isoformat().encode()).hexdigest()
        return THEMES[int(h[:8],16)%len(THEMES)]

    def _stats(self):
        c=self.db_factory()
        rows=c.execute("""select style,count(*) n,avg(passed) p,
                          avg(coalesce(attention_after,attention_before)-attention_before) d
                          from engagement_trials group by style""").fetchall()
        c.close()
        return {r["style"]:{"n":r["n"],"pass":float(r["p"] or 0),"delta":float(r["d"] or 0)} for r in rows}

    def choose_style(self,kind="study",after_failure=False):
        if after_failure:return "comeback"
        stats=self._stats()
        choices=[s for s in STYLES if s not in self.last_styles] or list(STYLES)
        best,best_score=None,-999.0
        for s in choices:
            st=stats.get(s,{"n":0,"pass":.55,"delta":0})
            explore=.22/math.sqrt(st["n"]+1)
            score=st["pass"]+max(-.15,min(.15,st["delta"]/100))+explore
            if kind in ("test","problem") and s in ("duel","precision","boss"):score+=.08
            if kind in ("read","recall") and s in ("mystery","teachback"):score+=.08
            if score>best_score:best,best_score=s,score
        self.last_styles.append(best);return best

    def wrap(self,instruction,style,seconds=60,streak=0,hook=""):
        prefix={"duel":"دوئل کوتاه:","mystery":"شکار نکته:","boss":"Boss:","precision":"ماموریت دقت:","sprint":"Sprint:",
                "teachback":"بعدش باید به ایلا درسش بدی:","streak":f"زنجیره {streak+1}:","comeback":"فرصت جبران:"}.get(style,"ماموریت:")
        text=f"{prefix} {instruction.strip()}"
        if hook and style=="mystery":text+=f" | سرنخ: {hook.strip()}"
        return {"display_instruction":text,"salience":f"این {max(20,int(seconds))} ثانیه فقط با شواهد یادگیری «برد» حساب می‌شود.","theme":self.daily_theme}

    def feedback(self,passed,style,streak):
        if passed:
            bank={"duel":"✓ این دوئل مال تو بود. بعدی.","mystery":"✓ نکته شکار شد. بعدی متفاوت است.","boss":"✓ Boss افتاد. مرحله بعد.",
                  "precision":"✓ دقیق بود. ثبت شد.","sprint":"✓ Sprint تمیز. دوباره قفل شو.","teachback":"✓ قابل توضیح بود. مفهوم تأیید شد.",
                  "streak":f"✓ streak={streak}. زنجیره را نشکن.","comeback":"✓ برگشتی. پرونده بسته."}
            return bank.get(style,"✓ تأیید شد. مأموریت بعدی.")
        bank={"duel":"✗ این دور باخت. اصلاح کوتاه، بعد دوئل بعدی.","mystery":"✗ نکته از دست رفت. یک سرنخ کوتاه و تلاش دوباره.",
              "boss":"✗ Boss هنوز زنده است. مسئله را کوچک‌تر می‌کنیم.","precision":"✗ خطای دقت. دلیل اشتباه را در یک جمله بگو.",
              "sprint":"✗ سرعت بدون شواهد حساب نمی‌شود. دور بعد آرام‌تر.","teachback":"✗ هنوز قابل توضیح نیست. Recall کوچک‌تر.",
              "streak":"✗ زنجیره شکست؛ جبران از همین هدف بعدی.","comeback":"✗ هنوز برنگشتی؛ هدف بعدی را نصف می‌کنیم."}
        return bank.get(style,"✗ این دور تأیید نشد. اصلاح کوتاه و دوباره.")

    def record_trial(self,style,passed,attention_before=None,attention_after=None,latency_ms=0):
        c=self.db_factory()
        c.execute("""insert into engagement_trials(ts,style,passed,latency_ms,attention_before,attention_after)
                     values(?,?,?,?,?,?)""",(int(time.time()),style,int(bool(passed)),int(latency_ms),attention_before,attention_after))
        c.commit();c.close()
