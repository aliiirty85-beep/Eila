from __future__ import annotations

class FutureEngine:
    def forecast(self,score:float,gaze:dict|None,micro:dict|None,risk:dict|None,flow:bool,rival:dict|None):
        gaze=gaze or {}; risk=risk or {"level":"low"}
        away=float(gaze.get("away_streak_seconds") or 0)
        if flow:
            now5="سکوت؛ Flow را نشکن."
        elif away>=8 or score<28:
            now5="RETURN فوری به همان micro-goal."
        elif risk.get("level")=="high":
            now5="افت نزدیک؛ انتخاب تازه نده، همان هدف را کوچک و واضح نگه دار."
        else:
            now5="فقط وضعیت را ببین؛ مداخله لازم نیست."

        if micro:
            remain=int(micro.get("remaining_seconds") or 0)
            if remain<=15:
                next60="منتظر تحویل همین هدف؛ بعد ✓/✗ و هدف بعدی."
            else:
                next60="همین micro-goal کافی است؛ هیچ انتخاب اضافه‌ای نساز."
        elif score<45:
            next60="یک micro-goal بیست تا چهل‌وپنج ثانیه‌ای با خروجی قابل تحویل بساز."
        else:
            next60="از محتوای فعلی یک micro-goal تازه، جذاب و قابل‌سنجش بساز."

        if rival:
            remaining=int(rival.get("remaining_seconds") or 0)
            u=float(rival.get("user_score") or 0); v=float(rival.get("rival_score") or 0)
            round10=f"دور رقابتی جاری: {remaining}s مانده؛ امتیاز تو {u:g} و رقیب {v:g}. کیفیت Recall بر سرعت اولویت دارد."
        else:
            round10="ده دقیقه آینده: زنجیره‌ای از micro-goalهای کوتاه با سنجش یادگیری."
        return {"now_5s":now5,"next_60s":next60,"round_10m":round10}
