# Failure Matrix

| خرابی | رفتار مطلوب |
|---|---|
| مدل آنلاین قطع | مدل بعدی → Ollama |
| همه AIها قطع | micro-goal دستی، Return Contract، memory، rival و command bus ادامه |
| اینترنت قطع | local/LAN و cache تا حد ممکن ادامه |
| لپ‌تاپ خاموش | Android cached commands/return reminders ادامه |
| گوشی gaze قطع | تبلت/desktop جایگزین؛ health هشدار |
| تبلت قطع | گوشی/desktop جایگزین |
| Vision fail | Active Source Context یا سؤال دستی |
| DB lock | WAL + busy_timeout |
| DB corruption | doctor + backup recovery |
| Core crash | launcher restart |
| crash-loop | safe-mode environment flag |
| API schema change | فقط AI Router/adapter تغییر کند |
| Android OS restriction | قابلیت sensor degrade شود، نه کل ایلا |
