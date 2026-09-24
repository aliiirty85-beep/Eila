# نگهداری خودکار ایلا

ایلا دو سطح نگهداری دارد:

1. **Self-heal runtime**: کاملاً خودکار. سلامت دیتابیس، backup، fallback مدل‌ها، دستگاه‌های stale و خطاهای runtime را بررسی می‌کند و تعمیرهای کم‌خطر را انجام می‌دهد.
2. **Self-improvement code**: test-gated. ایلا از خطاها proposal می‌سازد. اگر یک coding-agent آزاد/محلی نصب باشد، `maintenance_agent.py` proposal را داخل یک **کپی disposable** اجرا می‌کند، سپس compile/test می‌گیرد. کد live را کورکورانه بازنویسی نمی‌کند.

برای اتصال agent دلخواه:
`EILA_CODING_AGENT_CMD` را به دستور CLI آن agent بده و از placeholderهای `{prompt_file}` و `{workdir}` استفاده کن.

مثال مفهومی:
`<your-agent> --workdir {workdir} --prompt-file {prompt_file}`

قانون: `constitution.py` و `security.py` protected هستند. تغییر آنها توسط agent خودکار reject می‌شود.

هدف این طراحی «خودویرایش بی‌قید» نیست؛ هدف این است که ایلا بتواند مشکل را کشف کند، patch کاندید بسازد، تست کند و بدون به‌خطرانداختن نسخه سالم آماده ارتقا شود.
