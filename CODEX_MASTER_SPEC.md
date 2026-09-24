# Codex Master Spec — Eila Legend v2.0 LTS

این فایل برای مرحله‌ی بعد از تحویل است: Codex باید **کل repo** را audit کند و هیچ ادعای «کار می‌کند» را بدون build/test/hardware evidence نپذیرد.

## Non-negotiable behavior
- One active micro-goal at a time.
- WAIT for user output before moving on.
- Immediate verification + tiny feedback + immediate next goal.
- Short goals optimized for engagement **and verified learning**.
- Same Eila, different challenge: stable identity, varied stimulation.
- Flow Protection: silence is an active action during verified flow.
- Pre-Failure prediction should intervene before full derailment, not spam.
- Return Contracts must keep escalating locally on Android during ordinary server/network interruption.
- Gaze is probabilistic evidence, never mind-reading.
- Physical-book questions require actual page context (image/text); never invent unseen content.
- Paid AI is optional acceleration, never a critical dependency.
- Raw sensitive sensor data should not be retained long-term.
- Focus Firewall must never block urgent health/life messages.
- User remains owner of goals and final decisions.

## Architecture audit targets
- Python Core: FastAPI, SQLite/WAL, migrations, backup/recovery, launcher/doctor.
- Desktop sensing: active window, recent input, screen change, screenshot vision.
- Android: CameraX foreground service, MediaPipe Face Landmarker, per-device calibration, local return escalation, offline guard, voice, page capture.
- Multi-device continuity: pairing token, command bus, heartbeat, phone snapshot replica.
- AI Router: FAST/DEEP/VISION/JUDGE/RESEARCH, backoff/fallback.
- Web Brain: public-source retrieval → candidate summary; never self-modifying code/personality.
- Learning: evidence, pulse, error types, intervention outcomes.
- Motivation: novelty/anti-habituation/rival system.
- Security/privacy: trusted-LAN assumptions, cleartext-HTTP risk, token handling, file/context retention.

## Audit order
1. Run Core CI and Android build from a clean checkout.
2. Fix every build/test failure before new features.
3. Add integration tests for session → microgoal → feedback → next goal.
4. Hardware-test phone and tablet separately; quantify gaze-zone and screen-coordinate accuracy.
5. Measure battery/CPU and reduce sensor/network overhead where needed.
6. Test page-capture → image-context → relevant-question loop on real textbook pages.
7. Fault-inject internet/provider/device/db failures.
8. Threat-model LAN exposure and propose lowest-friction secure transport.
9. Benchmark local vs online model latency/quality.
10. Review every requirement in README/ARCHITECTURE against actual code and produce a missing-feature matrix.

Do not redesign for elegance at the cost of the behavioral loop. The user's primary requirement is a persistent, warm, strict study execution layer that keeps the next action tiny, attractive and explicit.
