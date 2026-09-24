# Eila Legend — v1.0 LTS

ایلا یک مربی مطالعه‌ی همیشه‌حاضر است که باید حتی با خراب‌شدن بخشی از سیستم، رشته‌ی کار را تا حد ممکن حفظ کند.

## اصل مرکزی
`detect → micro-goal → WAIT → response → verify → feedback → next`

در هر لحظه فقط یک قرارداد کوتاه فعال وجود دارد. جذابیت، رقابت، تازگی و فشار فقط زمانی خوب‌اند که شواهد واقعی یادگیری، Recall و دقت را بهتر کنند.

## معماری
- هویت ثابت + رفتار متنوع
- micro-goal جذاب و کوتاه
- Flow Protection و Intervention Budget
- Return Contract برای «۵ دقیقه دیگه برمی‌گردم»
- AI Router با fallback
- SQLite/WAL + backup
- Device Command Bus
- Gaze به‌عنوان سیگنال زمان‌بندی، نه ذهن‌خوانی
- Online-first / offline-survivable
- Paid AI اختیاری؛ Core نباید به اشتراک دلاری وابسته باشد

## مرز مهندسی
هیچ نرم‌افزاری را نمی‌شود صادقانه «تا ابد بدون هیچ تعمیر یا آپدیت» تضمین کرد. هدف LTS ایلا این است که تغییر یک API، مدل یا دستگاه، کل سیستم را از کار نیندازد و بازیابی ساده بماند.

## اجرای اولیه
1. Python 3.11 یا 3.12
2. `python -m venv .venv`
3. Windows: `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `python launcher.py`
6. مرورگر: `http://127.0.0.1:8765`

APIهای پولی کاملاً اختیاری‌اند. اگر تنظیم نشده باشند، Router می‌تواند از Ollama محلی استفاده کند.
