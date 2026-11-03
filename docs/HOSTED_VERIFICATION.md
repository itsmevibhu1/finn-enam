# Render verification — November 3, 2026

Service: https://finn-enam-l5x9.onrender.com

## Passed

- Public homepage, `/healthz`, `/snapshot.json` and `/api/capabilities` returned HTTP 200 without the owner's account.
- All eighteen mock-portfolio companies and the six initial research indexes were available.
- Twenty-six Chrome checks passed against the actual HTTPS deployment: primary-document retrieval, PDF-page links, historical comparisons, portfolio controls, gap states and four mobile layouts at 390px. No uncaught JavaScript exceptions were observed.
- An unfamiliar TCS ticker was collected through the hosted generic pipeline: six usable primary PDFs, 513 pages. Its index was retrieved, checked against the snapshot's SHA-256, and retained as a bundled asset for the next deployment. This expands bundled coverage to seven companies, forty-one documents and 3,657 pages.
- TCS has three distinct earnings periods in the target window; missing Q3 FY2026 stays explicit. Document count is not quarterly coverage.

## Generation limitation and repair

The first hosted Gemini request returned HTTP 503. A subsequent browser generation check also failed its success assertion; that run did not capture the displayed error text. Hosted generation was therefore not verified. No unsupported answer was presented as a successful draft. Local generation had previously passed, but that does not establish live cloud generation.

The adapter now retries HTTP 503 once after two seconds. Both attempts count toward the application cap. Persistent overload produces a clear message, with primary-document search still available. Authentication, quota and network errors do not receive automatic retries. Regression tests check successful retry, retry exhaustion and cap enforcement.

The repaired revision `53b0de0d8846da39a0917bcd6a868e87f02ddd6f` was confirmed active through the server revision endpoint. A subsequent full browser run passed all thirty checks against the public Render URL, including live Gemini generation, primary PDF-page citations and a cached repeat. The Python regression suite passed sixty-two tests. This verifies successful hosted generation after the repair; it does not prove the retry will resolve every provider outage. No paid model is selected automatically. The free host's runtime cache and request counter remain ephemeral across restarts, as documented in RENDER_DEPLOY.md.
