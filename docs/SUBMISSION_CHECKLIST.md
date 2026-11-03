# Submission checklist

## Prepared

- Publicly reachable phone-friendly prototype: https://finn-enam-l5x9.onrender.com
- GitHub source and reproducible setup: https://github.com/itsmevibhu1/finn-enam
- Five demo questions, the historical Infosys comparison and generic TCS onboarding proof: `DEMO_GUIDE.md`.
- Actual available local Codex conversation export: `AI_BUILD_HISTORY.md`, with redaction/provenance in `AI_BUILD_HISTORY_MANIFEST.json`. This is not a substitute for additional conversations if other AI tools were used.
- Draft covering email: `COVERING_EMAIL.md`. It has not been sent.
- Reproducible, small calibration set and results: `config/research_eval.json`, `data/announcement_eval.json`, `EVALUATION_RESULTS.json`.

## Required user actions before sending

1. Replace the API key exposed through IDE context if not already replaced. Update both `.env.local` and Render's secret value, and revoke the old key. Do not include keys in conversation exports or screenshots.
2. Source access is complete: the repository was made public with explicit user approval, and both the repository and redacted conversation URL returned HTTP 200 without authentication. Review the visible content before sending.
3. Read the exported conversation and covering email; add other AI conversations if used, and adjust the signature if desired.
4. Open the public service on a phone and run the short demo. The automated hosted checks do not replace a human phone check.
5. Confirm ENAM accepts the submission: the brief states November 1, 2026, and the build continued after that date. No extension has been assumed.
6. Send the email to `assessment@enam.com` with subject `ENAM - IIT screening - 2027` only after access and links are ready. Sending remains a separate user action or explicit authorization.

## Main limitations to disclose

- Rules prioritize observed NSE filings, but the rolling feed and archive do not establish complete historical coverage.
- EOD data is a dated snapshot, not a scheduled or intraday feed.
- INFY's FY25 promise/outcome case is curated. Automated structured financial extraction across companies is not implemented.
- AI quote/source checks are mechanical; they do not independently prove semantic interpretation, speaker attribution or accounting comparability.
- ASTRAL and TCS have explicit missing earnings quarters. A window ending at the latest indexed quarter does not prove no newer filing exists.
- Free hosting sleeps and loses runtime-only documents, caches, job state and the local request counter. The seven bundled company indexes survive redeployment.
- Gemini is an external service and can return overload/quota errors. One bounded overload retry is used; no paid-model fallback is automatic.
- Small, tuned calibration fixtures do not establish out-of-sample research or announcement accuracy.
