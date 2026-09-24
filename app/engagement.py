from __future__ import annotations
import hashlib, math
from collections import deque
from datetime import date

STYLES=("duel","mystery","boss","precision","sprint","teachback","streak","comeback")
THEMES=("رقابت","کنجکاوی","دقت","شکار خطا","بازگشت سریع","توضیح دادن","رکورد شخصی","آرامش عمیق")

class EngagementEngine:
    def __init__(self):
        self.last_styles=deque(maxlen=3)

    @property
    def daily_theme(self):
        h=hashlib.sha256(date.today().isoformat().encode()).hexdigest()
        return THEMES[int(h[:8],16)%len(THEMES)]

    def choose_style(self, kind="study", after_failure=False):
        if after_failure: return "comeback"
        choices=[s for s in STYLES if s not in self.last_styles] or list(STYLES)
        preferred={
          "test":("duel","precision","boss"),
          "problem":("precision","boss","sprint"),
          "read":("mystery","teachback"),
          "recall":("teachback","streak")
        }.get(kind,())
        style=next((x for x in preferred if x in choices),choices[0])
        self.last_styles.append(style)
        return style

    def wrap(self,instruction,style,seconds=60,streak=0):
        prefix={
          "duel":"دوئل کوتاه:","mystery":"شکار نکته:","boss":"Boss:",
          "precision":"ماموریت دقت:","sprint":"Sprint:",
          "teachback":"بعدش باید به ایلا درسش بدی:",
          "streak":f"زنجیره {streak+1}:","comeback":"فرصت جبران:"
        }.get(style,"ماموریت:")
        return {
          "display_instruction":f"{prefix} {instruction.strip()}",
          "salience":f"این {max(20,int(seconds))} ثانیه فقط با شواهد یادگیری «برد» حساب می‌شود.",
          "theme":self.daily_theme
        }

    def feedback(self,passed,style,streak):
        if passed:
            return f"✓ تأیید شد. streak={streak}. مأموریت بعدی."
        if style=="comeback":
            return "✗ هنوز برنگشتیم؛ هدف بعدی نصف می‌شود."
        return "✗ این دور تأیید نشد. یک اصلاح کوتاه، بعد دوباره."
