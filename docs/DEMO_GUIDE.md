# FINN reviewer walkthrough

Live prototype: https://finn-enam-l5x9.onrender.com

## Four-minute route

1. **Briefing:** show the default twenty-four-hour window, the feed's actual observed span, announcement filters and collapsed routine records. The dated snapshot is not a complete live filing archive.
2. **Portfolio:** show eighteen companies across sectors. Change the price/volume thresholds. Explain the prior twenty-session volume baseline and why stale observations cannot trigger alerts.
3. **Research → INFY:** open the historical FY25 promise tracker. Final growth of 4.2% exceeded the earlier Q1 range, met the Q2 range and missed the latest Q3 range by 0.3 percentage points. Open guidance and outcome sources. FY27 annual guidance remains pending.
4. **Research → HCLTECH:** choose earnings calls and latest four-quarter window. Submit the default question. Open a cited PDF page; repeat the question to demonstrate the validated cache.
5. **Cross-sector examples:** use one or two of the questions below. Inspect the quoted source before treating the interpretation as a finding.
6. **Honest gap:** select ASTRAL, earnings calls, Q4 FY2026. A missing transcript must produce an evidence gap. TCS's Q3 FY2026 gap is also explicit.

## Five research demo questions

| Company | Question | Document scope | Period |
| --- | --- | --- | --- |
| HCLTECH | What changed in management guidance and operating performance? | Earnings calls | Latest four-quarter window |
| DIXON | What did management say about capex? | Earnings calls | Latest four-quarter window |
| PERSISTENT | What did management say about operating margins? | Earnings calls | Latest four-quarter window |
| COFORGE | What did management say about growth guidance? | Earnings calls | Latest four-quarter window |
| ASTRAL | What are the raw material risks? | Annual reports | All periods |

The expected passages are recorded in `config/research_eval.json`. Keyword retrieval is bounded; these questions do not request or establish comprehensive company analysis.

## Generalization evidence

TCS was not among the six initial indexes. The generic hosted collector successfully imported six primary documents covering 513 pages. Its index is now bundled so that proof survives a free-host restart. To try a genuinely unindexed company, enter another NSE ticker such as POLYCAB and choose **Find company documents**. Collection can take several minutes and depends on primary-site access; a failed import should be visible, not replaced with invented evidence.

## Demo preparation

- Open the service before presenting. A free Render instance can require a cold start.
- Use the questions above once to warm the checked cache, within the application cap. Repeated questions avoid model calls while the same runtime and corpus remain available.
- Display the snapshot's session and refresh dates. Current market values are not promised by a saved deployment.
- Keep `.env.local` closed and avoid credential selections in IDE context or screenshots.
- Do not claim all eight suggested research views, fully automatic financial extraction, independent semantic verification, scheduled monitoring or complete exchange history.
