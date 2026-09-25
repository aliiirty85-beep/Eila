# EILA_CONTRACT — قرارداد واقعی ایلا

این سند معیار پذیرش ایلا است. هیچ قابلیت صرفاً به دلیل وجود کد «انجام‌شده» محسوب نمی‌شود.

وضعیت‌ها:
- **DONE + VERIFIED**: کد وجود دارد و با تست خودکار یا اجرای واقعی تأیید شده است.
- **IMPLEMENTED BUT UNVERIFIED**: پیاده‌سازی وجود دارد اما سخت‌افزار/رفتار طولانی‌مدت/یکپارچگی واقعی هنوز اثبات نشده است.
- **MISSING**: هنوز به سطح خواسته‌شده نرسیده است.

## 1) هویت و معماری
- DONE + VERIFIED — هویت/State ایلا از یک لپ‌تاپ خاص جدا شده و Spine revisioned دارد.
- DONE + VERIFIED — لپ‌تاپ به‌عنوان compute node قابل‌تعویض ثبت می‌شود.
- DONE + VERIFIED — event log idempotent، device lifecycle، conflict preservation و policy history وجود دارند.
- IMPLEMENTED BUT UNVERIFIED — بازیابی کامل روی لپ‌تاپ جدید از phone replica در یک سناریوی واقعی چنددستگاهی.
- MISSING — cloud replica production-grade با provider واقعی، rotation کلید، disaster-restore واقعی و تست چندمنطقه‌ای.

## 2) حلقه‌ی اصلی مطالعه
معیار غیرقابل‌مذاکره:
**detect → micro-goal → WAIT → response → verify → feedback → repair/retest when needed → next**
- DONE + VERIFIED — فقط یک micro-goal فعال است.
- DONE + VERIFIED — deadline به‌تنهایی task را fail یا replace نمی‌کند؛ WAIT ادامه دارد.
- DONE + VERIFIED — transport ACK پاسخ درسی محسوب نمی‌شود.
- DONE + VERIFIED — پاسخ خالی برای status=done پذیرفته نمی‌شود.
- DONE + VERIFIED — پاسخ غلط وارد repair و سپس retest می‌شود.
- IMPLEMENTED BUT UNVERIFIED — کیفیت محتوایی repair/retest روی درس واقعی در چندصد تعامل.
- MISSING — mastery update کاملاً کالیبره‌شده بر اساس نوع سؤال، دشواری، تأخیر و retention واقعی.

## 3) ایلا باید خودش آغازگر باشد
- DONE + VERIFIED — scheduler می‌تواند بدون پیام کاربر invitation یا follow-up تولید کند.
- DONE + VERIFIED — follow-upها bounded هستند و spam بی‌نهایت تولید نمی‌کنند.
- DONE + VERIFIED — Flow، Return Contract، stop و contextهای block-study حالت quiet ایجاد می‌کنند.
- DONE + VERIFIED — stop در حین درخواست AI اجازه ساخت orphan micro-goal نمی‌دهد.
- IMPLEMENTED BUT UNVERIFIED — رفتار proactive چندساعته/چندروزه روی گوشی واقعی.
- MISSING — سیاست proactive کاملاً شخصی‌سازی‌شده بر پایه‌ی outcomeهای بلندمدت.

## 4) Gaze و Screen Intelligence
- IMPLEMENTED BUT UNVERIFIED — Android Gaze Service، calibration جدا برای هر دستگاه، gaze metrics و device heartbeat.
- IMPLEMENTED BUT UNVERIFIED — Screen capture و crop نزدیک gaze برای سؤال.
- IMPLEMENTED BUT UNVERIFIED — صفحه کتاب از طریق image context.
- MISSING — benchmark واقعی precision/recall ناحیه نگاه روی گوشی و تبلت کاربر.
- MISSING — drift correction خودکار در نشست طولانی و calibration confidence score پایدار.
- MISSING — semantic layout model کامل که paragraph/question/option/figure را به‌صورت ساختاریافته دنبال کند.

## 5) Voice
- IMPLEMENTED BUT UNVERIFIED — VoiceActivity، speech recognition و TTS integration وجود دارند.
- MISSING — voice-first continuous interaction با wake/turn management قابل اتکا.
- MISSING — تست طولانی‌مدت latency، قطع شبکه، TTS fallback و interruption handling روی دستگاه واقعی.

## 6) Return Contract
- DONE + VERIFIED — قرارداد بازگشت time-bound ذخیره و escalate می‌شود.
- DONE + VERIFIED — acknowledge مسیر مستقل دارد.
- IMPLEMENTED BUT UNVERIFIED — notification/vibration/TTS escalation روی Android واقعی.
- MISSING — benchmark قابل اتکا برای delivery هنگام Doze/Android background restrictions روی مدل‌های مختلف دستگاه.

## 7) حافظه و مدل دانش‌آموز
- DONE + VERIFIED — memory دسته‌بندی‌شده، Student Model، Error Genome، review queue و behavior model وجود دارند.
- DONE + VERIFIED — خطا repair سریع و مرور فاصله‌دار تولید می‌کند.
- IMPLEMENTED BUT UNVERIFIED — کیفیت taxonomy خطاها در استفاده واقعی.
- MISSING — forgetting curve شخصی‌سازی‌شده و calibration بر اساس retention چندروزه/چندهفته‌ای.

## 8) Live Evolution
- DONE + VERIFIED — درخواست‌های رفتاری می‌توانند policy versioned/rollbackable شوند.
- DONE + VERIFIED — actionهای خارج از allowlist مستقیماً live اجرا نمی‌شوند.
- IMPLEMENTED BUT UNVERIFIED — تبدیل زبان طبیعی «از این به بعد...» به policy درست روی مدل‌های واقعی.
- IMPLEMENTED BUT UNVERIFIED — capability request pipeline و isolated coding-agent candidate.
- MISSING — promotion production-grade با approval/CI/rollback خودکار و audit trail کامل از ابتدا تا انتها.

## 9) Self-maintenance / self-repair
- DONE + VERIFIED — DB integrity، backup، recovery primitive، runtime health و maintenance proposals.
- DONE + VERIFIED — coding-agent candidate روی کپی جدا کار می‌کند و live code را مستقیم rewrite نمی‌کند.
- IMPLEMENTED BUT UNVERIFIED — recovery از خرابی واقعی DB و provider failure در دستگاه کاربر.
- MISSING — watchdog مستقل OS-level، service install، reboot recovery و crash-loop remediation production-grade.

## 10) چنددستگاهی
- DONE + VERIFIED — registry، heartbeat، capabilities، device retirement/replacement، sync protocol و event idempotency.
- DONE + VERIFIED — divergent same-revision state silently overwrite نمی‌شود و conflict ذخیره می‌شود.
- IMPLEMENTED BUT UNVERIFIED — handoff واقعی phone ↔ tablet ↔ laptop بدون state loss.
- MISSING — latency/partition tests چندساعته و conflict resolution UX برای کاربر.

## 11) Offline / resilience
- IMPLEMENTED BUT UNVERIFIED — local guard، cached state، Return Contract و local components.
- MISSING — اثبات عملی Survival Mode وقتی laptop خاموش + اینترنت قطع است.
- MISSING — local mobile inference واقعی برای سؤال‌های پایه بدون Core.
- MISSING — OS service/boot reliability روی Windows و Android در چرخه reboot کامل.

## 12) رقابت / Ball Rival
- DONE + VERIFIED — Ball Rival telemetry از learning evidence جداست.
- DONE + VERIFIED — rival scoring primitive وجود دارد.
- IMPLEMENTED BUT UNVERIFIED — اثر رقابت واقعی بر recall/accuracy کاربر.
- MISSING — experiment policy که stimulus را بر اساس outcome واقعی خودکار کم/زیاد کند.

## 13) امنیت و حریم خصوصی
- DONE + VERIFIED — pairing token برای LAN API وجود دارد.
- DONE + VERIFIED — protected code files در maintenance candidate gate محافظت می‌شوند.
- IMPLEMENTED BUT UNVERIFIED — raw gaze/video عمداً persist نمی‌شود؛ تست forensic کامل انجام نشده.
- MISSING — TLS/local encrypted transport production-grade؛ LAN cleartext هنوز limitation است.
- MISSING — cloud key management و encrypted backup restore production-grade.

## 14) تجربه نصب و استارت
- DONE + VERIFIED — setup ویندوز Python 3.11/3.12 را صریح انتخاب می‌کند.
- DONE + VERIFIED — Launcher crash output را در logs/core.log ذخیره می‌کند.
- DONE + VERIFIED — CI واقعاً Uvicorn را بالا می‌آورد و /api/health را صدا می‌زند.
- MISSING — one-click first-run که setup، start، health wait، dashboard، backup و pairing info را بدون دستورهای دستی انجام دهد.
- MISSING — installer/package واقعی Windows.
- MISSING — auto-update امن با rollback.

## 15) معیار «نسخه قابل استفاده»
ایلا تا زمانی که تمام این vertical slice روی دستگاه واقعی پاس نشده، نهایی محسوب نمی‌شود:
1. first-run تمیز؛
2. Core health؛
3. dashboard؛
4. pairing phone؛
5. heartbeat؛
6. start session؛
7. micro-goal؛
8. WAIT؛
9. correct feedback؛
10. wrong feedback؛
11. repair؛
12. retest؛
13. Return Contract؛
14. Core restart؛
15. continuity restore؛
16. reconnect phone؛
17. no duplicate command؛
18. backup exists؛
19. stop واقعی؛
20. reboot/long-session hardware validation.

اصل توسعه: **feature count معیار نیست؛ verified behavior معیار است.**
