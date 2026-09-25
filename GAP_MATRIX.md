# GAP_MATRIX — شکاف‌های واقعی ایلا

## P0 — قبل از هر قابلیت جدید
| شکاف | وضعیت | معیار خروج |
|---|---|---|
| One-click Windows first run | MISSING | یک فایل را اجرا کنیم؛ setup/start/health/dashboard/backup بدون دستور دستی |
| Vertical slice end-to-end | PARTIAL | session→micro→WAIT→wrong→repair→retest→return→restart→restore با integration test |
| Real phone pairing | UNVERIFIED | heartbeat و command ACK روی گوشی واقعی |
| Long-running Core stability | UNVERIFIED | حداقل 4 ساعت بدون crash/hang و با health latency قابل قبول |
| Android long-run foreground reliability | UNVERIFIED | Gaze service چندساعته + reconnect |
| Real laptop replacement | UNVERIFIED | Core تازه + replica restore بدون توضیح دوباره state |
| Hardware backup/restore drill | UNVERIFIED | خرابی عمدی/DB restore و continuity |

## P1 — کیفیت تجربه اصلی
| شکاف | وضعیت | معیار خروج |
|---|---|---|
| Gaze accuracy benchmark | UNVERIFIED | dataset کوچک واقعی و confusion matrix zoneها |
| Gaze drift handling | MISSING | drift detection + recalibration hint |
| Voice-first reliability | PARTIAL | voice turn + interrupt + reconnect بدون touch-heavy UX |
| Screen semantic grounding | PARTIAL | سؤال به paragraph/question/figure واقعی متصل باشد |
| Repair/retest quality | PARTIAL | >90% repair مرتبط در نمونه آزمون دستی |
| Notification delivery under Android constraints | UNVERIFIED | تست Doze/background |
| Flow silence personalization | PARTIAL | intervention count و learning outcome ثبت و tune شود |

## P2 — هوشمندی شخصی‌سازی
| شکاف | وضعیت | معیار خروج |
|---|---|---|
| Forgetting curve شخصی | MISSING | schedule از retention واقعی یاد بگیرد |
| Experiment engine | PARTIAL/MISSING | A/B مداخله + outcome + keep/discard |
| Counterfactual intervention value | MISSING | مداخله بی‌اثر کاهش یابد |
| Curiosity engine | PARTIAL | سؤال‌های کنجکاوی source-grounded |
| Rival effectiveness adaptation | MISSING | رقابت فقط وقتی outcome را بهتر می‌کند شدت بگیرد |
| Behavior model calibration | PARTIAL | زمان/درس/نوع task به failure risk وصل شود |

## P3 — مقاومت پیشرفته
| شکاف | وضعیت | معیار خروج |
|---|---|---|
| Windows service/watchdog | MISSING | reboot→Eila returns بدون کار دستی |
| Cloud replica provider | ABSTRACTION ONLY | encrypted provider + restore drill |
| TLS/local secure transport | MISSING | cleartext LAN حذف شود |
| Mobile local inference | MISSING | laptop/internet unavailable و سؤال پایه ادامه یابد |
| Auto-update with rollback | MISSING | candidate→canary→promote→rollback |
| Full disaster recovery package | PARTIAL | device loss scenario مستند و تست‌شده |

## قانون اولویت
تا وقتی P0 سبز نشده، هیچ novelty/visual/feature تزئینی جدید وارد branch production candidate نمی‌شود.
