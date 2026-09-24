# Failure Matrix

| خرابی | رفتار مطلوب |
|---|---|
| مدل آنلاین قطع | provider بعدی → Ollama |
| همه AIها قطع | timer/micro-goal/Return Contract/memory ادامه |
| اینترنت قطع | LAN/local در صورت وجود؛ state محلی حفظ |
| لپ‌تاپ خاموش | Android cached guard و قرارداد بازگشت ادامه |
| یک Android قطع | دستگاه دیگر/desktop ادامه |
| DB lock | WAL + busy_timeout |
| Core crash | launcher restart |
| crash-loop | Safe Mode |
| DB خراب | integrity check + backup |
| API provider تغییر | فقط Router/config تغییر کند |

این ماتریس تضمین جاودانگی نیست؛ برای محدودکردن دامنه‌ی خرابی است.
