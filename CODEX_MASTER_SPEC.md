# Codex Master Spec — Eila Legend

این فایل برای مرحله‌ی بعد از تحویل v2.0 است. Codex باید ابتدا کل repo را audit کند و فقط بر اساس evidence تغییر دهد.

## Non-negotiable
- One active micro-goal at a time.
- WAIT for user output before moving on.
- Immediate verification and tiny feedback.
- Short-term goals optimized for engagement + verified learning.
- Same Eila, different challenge: identity stable, stimulation varied.
- Flow Protection: when verified flow is good, silence is an action.
- Return Contracts must survive ordinary app interruptions.
- Gaze is probabilistic evidence, never mind-reading.
- Paid AI is optional acceleration, never critical dependency.
- Raw sensitive sensor data should not be retained long-term.

## Codex audit order
1. Run Python CI and Android build.
2. Fix all build/test failures before feature additions.
3. Threat-model privacy/network exposure.
4. Hardware-test Android camera foreground service and per-device calibration.
5. Validate gaze accuracy empirically on phone and tablet separately.
6. Validate screenshot-to-question relevance using real study pages.
7. Fault-inject internet/provider/device/db failures.
8. Benchmark latency and CPU/battery.
9. Only then optimize prompts/models/UI.

Never claim a feature works because code exists; require build/test/hardware evidence appropriate to that feature.
