# Eila Spine v3 — development branch

ایلا یک مربی مطالعه‌ی همیشه‌حاضر، گرم، فعال و مقاوم در برابر خرابی است. هسته‌ی کار یک چرخه‌ی کوتاه و پیوسته است:

**detect → micro-goal → WAIT → response → verify → feedback → next**

## قابلیت‌های اصلی این نسخه
- Attractive MicroGoals با سبک‌های duel / mystery / boss / precision / sprint / teach-back / streak / comeback
- Novelty Engine و Anti-Habituation: هویت ثابت، شکل چالش متغیر
- Hyperfocus Ramp: RAMP → LOCK → FLOW → RECOVER
- Flow Protection: وقتی تمرکز واقعی خوب است، سکوت ایلا یک تصمیم فعال است
- Pre-Failure Risk و سه افق ۵ ثانیه / ۱ دقیقه / ۱۰ دقیقه
- Desktop sensing خودکار: active window، recent input، screen change؛ بدون ذخیره‌ی خام screenshot
- Personalized Gaze روی هر Android با calibration جداگانه
- Gaze events: long fixation / rapid revisit / flighty / away streak
- سؤال دقیق از همان نقطه‌ی مورد توجه با Screen Vision
- برای کتاب فیزیکی: عکس full-resolution صفحه از Companion → Active Image Context → سؤال مرتبط
- Active text source برای متن/جزوه
- Learning Pulse و Study Integrity برای فرق‌گذاشتن بین فعالیت ظاهری و یادگیری
- Return Contract با escalation محلی روی گوشی: notification → vibration → TTS
- دکمه‌ی «برگشتم» روی اعلان Return Contract
- Local Survival Guard وقتی لپ‌تاپ/شبکه در دسترس نیست
- Voice conversation از Companion با speech recognition + TTS
- Study Firewall و Later Inbox در Focus Mode
- Rival/Taha 10-minute engine با multiplier پیش‌فرض 1.07
- حافظه‌ی طبقه‌بندی‌شده: mastery / error / behavior / decision / context / commitment / preference
- Phone replica snapshot برای حفظ state فشرده و memory
- Daily Web Brain از PubMed/arXiv/RSS و distillation با مدل Research
- FAST / DEEP / VISION / JUDGE / RESEARCH router با provider fallback
- Ollama به‌عنوان fallback رایگان؛ API پولی اختیاری است
- SQLite/WAL، schema migration، backup دوره‌ای، recovery از backup، doctor و launcher auto-restart
- Pairing token برای درخواست‌های LAN از گوشی/تبلت
- CI مستقل برای Core و Android APK

## اصل هزینه
قابلیت حیاتی نباید به ChatGPT Plus یا API دلاری وابسته باشد. مدل‌های پولی فقط Turbo هستند. اگر همه‌ی providerهای آنلاین قطع شوند، قرارداد بازگشت، memory، rival، cached microgoal و نگهبانی پایه باقی می‌مانند؛ کیفیت سؤال عمیق ممکن است پایین‌تر شود.

## Windows
1. Python 3.11 یا 3.12 نصب کن.
2. \`setup_windows.bat\`
3. برای fallback رایگان، Ollama را نصب کن.
4. \`run_windows.bat\`
5. داشبورد: \`http://127.0.0.1:8765\`
6. \`show_token.bat\` را اجرا کن و token را در Companion وارد کن.

## Android
APK از GitHub Actions workflow **Build Eila Android** ساخته می‌شود.
بعد از نصب:
1. IP لپ‌تاپ و Pairing Token را وارد کن.
2. Gaze را از صفحه‌ی اصلی شروع کن.
3. برای هر گوشی/تبلت یک بار Calibration جدا انجام بده.
4. برای کتاب فیزیکی، «عکس صفحه کتاب / منبع فعال» را بزن.
5. Voice برای گفت‌وگوی کوتاه با ایلا در دسترس است.

## محدودیت صادقانه
هیچ نرم‌افزاری را نمی‌شود «تا ابد بدون حتی یک تغییر» تضمین کرد؛ Android، Windows و APIها تغییر می‌کنند. v2.0 عمداً طوری طراحی شده که خرابی یا تغییر یک جزء تا حد ممکن فقط همان قابلیت را ضعیف کند، نه کل ایلا را.

Gaze نیز ذهن‌خوانی نیست. calibration و تست سخت‌افزاری واقعی روی گوشی/تبلت خود کاربر برای تعیین دقت لازم است.


<!-- Eila Spine v3 development branch -->


## Eila Spine: هویت مستقل از دستگاه

در v3 لپ‌تاپ دیگر «خانه ایلا» نیست. هویت، state، policyها و eventهای ایلا از device جدا شده‌اند. گوشی، تبلت و لپ‌تاپ فقط Node هستند.

- `spine_state`: state canonical و revisioned.
- `events`: event log با `event_id` یکتا؛ retry یک event را دوبار اجرا نمی‌کند.
- `devices`: Device Registry با active/retired، hardware fingerprint و revision.
- `device_snapshots`: replica فشرده برای بازیابی روی لپ‌تاپ جدید.
- Sync protocol v3: snapshot + event tail + conflict-aware Spine replication.

### تعویض لپ‌تاپ

1. Eila Core را روی لپ‌تاپ جدید نصب می‌کنی.
2. Companion گوشی/تبلت به Core جدید pair می‌شود.
3. Node جدید hardware/capabilities خود را اعلام می‌کند.
4. snapshot ذخیره‌شده گوشی به Core offer می‌شود.
5. stateهایی که روی Core جدید نیستند از replica برمی‌گردند.
6. مدل‌های حجیم AI cache محسوب می‌شوند و می‌توانند دوباره دانلود شوند.
7. فقط calibrationهای وابسته به هندسه دوربین/نمایشگر دوباره انجام می‌شوند.
8. لپ‌تاپ قدیمی در Registry به `retired` تبدیل می‌شود؛ هویت ایلا عوض نمی‌شود.

## Live Evolution

درخواست‌هایی مثل «از این به بعد...» می‌توانند به policy versioned تبدیل شوند. policyهای رفتاری امن hot-reload می‌شوند؛ درخواست‌هایی که سنسور/API/permission یا کد جدید می‌خواهند به `capability_request` تبدیل می‌شوند و نباید مستقیم live code را بازنویسی کنند.

هر policy:
- scope
- trigger
- action
- priority
- version
- source/rationale
- history

دارد و قابلیت disable/rollback برای آن در Core پیش‌بینی شده است.

## Student Model / Error Genome

v3 علاوه بر Learning Pulse، برای topicها attempts/correct/mastery/next_due نگه می‌دارد. پاسخ غلط:
- به Error Genome اضافه می‌شود،
- repair سریع را برنامه‌ریزی می‌کند،
- سپس retest هم‌مفهوم می‌آید،
- و مرورهای بعدی به‌تدریج فاصله می‌گیرند.

## وضعیت validation

این شاخه عمداً از `main` جدا نگه داشته می‌شود تا نسخه پایدار قربانی توسعه نشود. تغییرات v3 تا قبل از build/test gate کامل نباید به‌عنوان نسخه production معرفی شوند. Hardware-dependent claims مثل دقت Gaze، مصرف باتری و handoff واقعی گوشی↔تبلت↔لپ‌تاپ باید روی دستگاه واقعی benchmark شوند.
