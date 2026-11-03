# Research interface milestone — November 3, 2026

## Verified behavior

- Local Research now offers a question form for any indexed company when Gemini is configured server-side.
- Document-type and reporting-period filters apply to the model's retrieved evidence.
- Bounded background jobs expose queued/running/complete/failed states. Identical concurrent questions share a job. The API key never enters browser assets.
- Drafts retain checked exact quotations and trusted source-page links. Interpretations remain labelled AI drafts; matching quotations alone does not establish semantic correctness.
- Repeat questions with identical evidence, model and prompt use the validated disk cache. The application-wide daily request cap remains active.
- No-match results do not call Gemini. Unknown companies must first be collected and indexed.

## Validation

- 57 Python tests passed, including request validation, cross-origin rejection, duplicate-job handling, result preservation, quote validation, credential handling and quota limits.
- JavaScript retrieval, filing and market-signal suites passed.
- 30 Chrome checks passed, including a live generation through the question form, source-page links, cached repeat, and four mobile views at 390px.
- Earlier HCLTECH request: 104.24 seconds and two attempts. After requesting shorter exact quotes: a different filtered HCLTECH request took 33.78 seconds and one attempt. This is a small functional sample, not a controlled latency benchmark.

## Run

```sh
python3 scripts/serve.py --port 8000
```

Open http://127.0.0.1:8000/#research. Select HCLTECH, choose earnings calls and the latest four-quarter window, and submit the default question to reuse the tested cached draft in the original workspace.

## Remaining

The static Sites deployment does not execute Python. Hosted generation and new-company ingestion require a server deployment. New users/clones need their own ignored `.env.local`; caches and credentials are excluded from source sync. External reviewer access, GitHub upload, broader research evaluation, actual conversation exports and submission email remain to be completed.
