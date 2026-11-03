# Iteration 2 — November 3, 2026

## What changed

The prototype now retrieves evidence from primary documents for six companies instead of only displaying the original Infosys case study. No model API account or paid inference is needed for document discovery, PDF parsing, keyword ranking, or financial-rule calculations.

## Measured coverage

| Company | Usable primary PDFs | Notes |
|---|---:|---|
| INFY | 5 | Annual report and company-call transcripts; media calls and an investor event are labelled separately. |
| HCLTECH | 5 | Annual report and four earnings-call transcripts. |
| PERSISTENT | 5 | Annual report and company-call transcripts, including a special investor call. |
| DIXON | 5 | Annual report and four earnings-call transcripts. |
| ASTRAL | 1 | Annual report only; an audio-recording notice and three broken transcript links were excluded. |
| COFORGE | 5 | Additional company outside the original demo set, collected through the same generic pipeline. |

Total: **26 PDFs, 2,914 PDF pages, six corpora**. Each corpus is loaded only when selected. The full generated text indexes total about 10.9 MB before compression. Source PDFs and extracted originals remain in ignored local storage; the private hosted application includes searchable derived indexes.

The browser returns at most one short excerpt per matching document, with source URL, original PDF page, and SHA-256 document identity. Keyword matching is not semantic understanding and does not establish that a passage is management guidance or comparable financial evidence. Generated analysis remains unimplemented.

## Exchange-feed correction

The first report incorrectly described NSE RSS as HTTP-blocked. The API was HTTP-blocked, while RSS returned a non-RFC date format that our parser rejected. The parser now accepts that format and skips individually malformed timestamps instead of failing the entire feed.

The successful November 3 morning RSS response contained 185 dated exchange items, spanning approximately midnight to 07:00 IST, with **zero matched portfolio disclosures**. This is a source snapshot result, not evidence that there were no filings outside that observed period. It cannot provide a complete seven-day history. Subsequent successful refreshes accumulate observed events in an archive.

The UI defaults to a 24-hour current window, shows the feed's observed span, keeps unknown categories visible, collapses routine disclosures, filters categories, and groups duplicate attachments. The older Infosys event remains available through an explicitly labelled replay.

## Price freshness

The November 3 refresh returned data for all 18 companies, but all latest returned sessions remained October 30. Successful fetches are not described as fresh market data. The portfolio screen states session date separately from refresh-attempt time. A newer completed session has not been verified.

## Local versus hosted behavior

- Hosted: search the six prebuilt primary-document corpora; inspect source evidence; use the existing financial comparisons, portfolio, and snapshot briefing.
- Local server: enter a new ticker, start a bounded source-collection job, inspect progress, and search its imported primary documents after indexing.
- Still absent: hosted background ingestion, scheduled refresh, live generation, and unrestricted arbitrary-ticker onboarding from the hosted site.

## API access

The user has ChatGPT Plus and no model API key. No API calls or purchases were made. An evidence pack can be exported for manual review in a chat. That manual step is separate from runtime automated research. The model-provider decision remains open.

## Validation

- 25 Python tests passed, covering financial comparisons, date parsing, source-domain boundaries, source-type checks, reporting-quarter metadata, and local API input handling.
- 11 JavaScript retrieval/filing tests passed, covering source/page preservation, evidence gaps, excerpt limits, guidance-query variants, unrelated-forecast exclusion, duplicate grouping, routine/unknown categories, and time-window filtering.
- 22 browser checks passed: multi-company retrieval, the additional Coforge ticker, source-page/hash inspection, explicit no-match results, local new-ticker controls, portfolio settings, and mobile layouts across all four views.

These are functional and regression checks, not an independently labelled financial-extraction accuracy benchmark. Automated numeric extraction is not implemented.

## Next priorities

1. Add validated structured extraction and generated synthesis after selecting a model-access route; keep all conclusions source-linked.
2. Host a backend/ingestion job system so reviewers can add unfamiliar tickers without running the local server.
3. Add a reliable historical exchange source and verify weekday market-data freshness. Rolling RSS alone cannot establish complete coverage.
4. Select the latest four *earnings calls* per company instead of assuming every directory transcript is quarterly. Fetch additional candidates when special events displace a quarter.
5. Improve retrieval with reporting-period filters and measure relevance against manually checked questions. Longer tables need robust structured extraction.
6. Finish the GitHub repository, actual AI-conversation exports, externally accessible submission hosting, and covering note. The original November 1 deadline has passed; no extension is assumed.
