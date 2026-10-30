# Build plan

## Scope decisions

Build a responsive web app for quick phone access. Start with Python for data ingestion, extraction, and deterministic financial calculations. Keep UI and hosting decisions open until a source-to-evidence slice works; the local environment currently has Python and Poppler but no Node runtime.

The first company is INFY. Proposed ad-hoc research examples are HCLTECH, PERSISTENT, DIXON, and ASTRAL, subject to checking primary-document availability. These are demonstration choices, not investment recommendations.

## Delivery order

### 1. One company, verified evidence

- Find one annual report and the last four available quarterly transcripts/results through the company's investor-relations archive.
- Preserve source URL, reporting period, retrieval time, original bytes, and PDF page number.
- Manually identify one explicit, measurable management promise before automating extraction.
- Match it to a subsequent reported outcome using the same metric, period, units, and accounting scope.
- If suitable guidance is unavailable, report that fact or select another company rather than inventing a comparison.

Acceptance: another person can open the source documents and reproduce one comparison. Annual guidance is not graded as a miss using a partial year. A future outcome remains pending.

### 2. Working research screen

- Render business context, the promise/outcome comparison, and clickable evidence in a phone layout.
- Support ticker input using generic discovery and ingestion logic.
- Display missing sources and processing status clearly.
- Extract facts into structured records; calculate changes in code; ask a model only for evidence-grounded interpretation.

Acceptance: a second company outside the initial demo set goes through the same pipeline. Unsupported evidence produces an explicit gap, not a fabricated answer.

### 3. Portfolio inbox

- Fetch corporate announcements and EOD prices/volumes for 18 configured companies.
- Preserve exchange timestamps and fetch timestamps separately.
- Implement window selection, materiality ranking, related-document grouping, and expandable routine disclosures.
- Compare volume with a stated prior-session average excluding the current session; make price/volume thresholds configurable.
- Display why an alert triggered. EOD detection is after daily data becomes available, not intraday monitoring.

Acceptance: a labelled historical window reliably demonstrates both useful alerts and suppressed routine filings. Refresh remains available; failures show last-successful-fetch time.

### 4. Validate and submit

- Check roughly 20 announcement examples and 5 promise comparisons manually; report observed accuracy and misses without inventing scores.
- Test PDF parsing failures, duplicate documents, mismatched financial units, unfamiliar tickers, and missing guidance.
- Cache document parsing and extraction by content hash and extraction version. Track model usage, cost, and latency.
- Deploy, verify mobile access, document setup, and export actual AI build history.
- Prepare the covering email and repository links. Sending the submission is a separate user-authorized step.

## Minimal research record

Each claim needs: ticker; metric; stated period; value/range; units; standalone/consolidated scope; source document ID; PDF page; supporting passage; extraction version; validation status.

Each comparison needs: promise record; outcome record; matching rationale; deterministic calculation if appropriate; status (`met`, `missed`, `pending`, `not_comparable`, or `insufficient_evidence`); short interpretation.

Quote or distinguish qualitative commentary separately from explicit numerical guidance. Revisions have dates and do not overwrite earlier promises. Revenue, margins, and growth rates must use comparable definitions. Store reported and derived metrics separately. PDF page numbering and printed page numbering may differ; identify which is shown.

## Deliberately defer

Voice, native app packaging, brokerage integration, buy/sell recommendations, elaborate multi-agent infrastructure, and attempting all eight research views before the two main workflows work.

## Model configuration later

Choose a provider after checking available API access. A paid chat subscription must not be assumed to supply programmatic model access. Keep provider credentials server-side, outside source control. No model access is required for local document import.
