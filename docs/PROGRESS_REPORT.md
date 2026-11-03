# First prototype report — October 30, 2026

Historical report. See `ITERATION_2_REPORT.md` for current status. Correction established November 3: the NSE API was HTTP-blocked, but RSS failed because of an unsupported date format; the original statement that both paths returned HTTP 403 was inaccurate.

## Delivered

A functional responsive web prototype with four views: a dated briefing, management-guidance research, an 18-company portfolio, and primary-source references.

The research records were manually checked through the web PDF reader. Financial verdicts are deterministic code. This distinction is visible in the product. There is no claim that an automated AI research pipeline has been completed.

## Research finding

Infosys's FY25 constant-currency revenue growth was 4.2%. This exceeded the Q1 guidance range of 3–4%, met the Q2 range of 3.75–4.5%, and missed the Q3 range of 4.5–5% by 0.3 percentage points against its lower bound. FY25 operating margin of 21.1% was within the 20–22% guidance range.

Source-page references:

- Q1 transcript, July 18, 2024, PDF page 5: https://www.infosys.com/investors/reports-filings/quarterly-results/2024-2025/q1/documents/transcripts/earningscall.pdf#page=5
- Q2 transcript, October 17, 2024, PDF page 4: https://www.infosys.com/investors/reports-filings/quarterly-results/2024-2025/q2/documents/transcripts/earningscall.pdf#page=4
- Q3 transcript, January 16, 2025, PDF page 7: https://www.infosys.com/investors/reports-filings/quarterly-results/2024-2025/q3/documents/transcripts/earningscall.pdf#page=7
- Q4 transcript, April 17, 2025, PDF page 3: https://www.infosys.com/investors/reports-filings/quarterly-results/2024-2025/q4/documents/transcripts/earningscall.pdf#page=3
- FY25 annual report, PDF page 73 corroborates growth; publication date was not established. It is excluded from the April 17 event replay: https://www.infosys.com/investors/reports-filings/annual-report/annual/documents/infosys-ar-25.pdf#page=73

The October 23, 2026 call's FY27 growth range of 1–2% is represented as pending because the fiscal year ends in March 2027. Source: https://www.infosys.com/investors/reports-filings/quarterly-results/2026-2027/q2/documents/transcripts/earningscall.pdf#page=3

## Data results

- Yahoo Finance daily chart data succeeded for 18 of 18 configured companies. Latest included session: October 30, 2026.
- Default thresholds are an absolute daily price move of 3% or volume of 2× the prior 20 completed sessions. The latest session is excluded from the volume average.
- The recorded snapshot triggers INFY on price (+3.358%), SUNPHARMA on volume (3.4225×), and VSTIND on volume (2.2907×). These are mechanical rules, not investment conclusions or explanations of price movements.
- NSE's public announcement API and official RSS returned HTTP 403. No portfolio-wide filing feed is claimed.
- Direct downloads of 18 attempted Infosys PDFs returned HTTP 403. Six source references were inspected using the web PDF reader; full source text is not indexed.
- LLM API usage in the prototype: zero. Infrastructure costs and subscription costs have not been measured.

## Validation

12 Python tests passed. They check exact guidance deltas, revision outcomes, mismatched accounting/period bases, future outcomes, publication-date leakage, missing evidence, volume baseline selection, configurable thresholds, and conservative unknown-announcement handling.

15 browser checks passed using installed Chrome. These cover navigation, original PDF page links, research coverage gaps, all 18 displayed prices, source-summary search, portfolio filtering, threshold persistence, and no horizontal page overflow at 390px across all four views. No uncaught JavaScript exceptions were observed during those flows. Desktop and mobile screenshots were inspected locally.

This is a small verified case study, not a measured extraction-accuracy benchmark. Human phone testing and external reviewer access remain useful checks.

## Improvement priorities

1. **General research pipeline:** add source discovery for arbitrary NSE tickers, reliable primary-document ingestion, structured model extraction, and claim validation. This is the largest gap against the assignment. Add 3–5 ad-hoc companies and verify unfamiliar-ticker behavior with real sources.
2. **Reliable exchange feed:** use an accessible permitted data source or approved exchange data access; persist historical filings. Then add deduplication, materiality ranking, routine-item collapsing, and user-selected announcement categories. Current collectors fail visibly rather than fabricate a feed.
3. **Latest four-quarter coverage:** the completed research case uses FY25 deliberately to demonstrate assessable delivery. Expand to the latest four quarters and keep unfinished annual guidance pending.
4. **Full source inspection:** store original PDFs or stable primary-source equivalents and expose exact passages with page highlights. Current cards provide verified paraphrases and external page links only.
5. **Automatic freshness:** run ingestion on a schedule and publish snapshots, or add a backend with job status, last-success timestamps, and refresh controls. The deployed app currently reads a saved snapshot.
6. **Broader quality evidence:** assemble the planned 20-announcement/5-comparison annotated set, measure extraction support and missed material events, and record model cost/latency once model calls exist.
7. **Submission packaging:** create the GitHub submission repository, export actual AI conversations, and prepare the covering note. Sites source hosting is not a substitute for the requested GitHub link. Private prototype hosting is not yet an externally accessible ENAM submission link.

## Architecture

Python standard-library collectors → versioned JSON records → deterministic comparison engine → static JSON snapshot → buildless HTML/CSS/JS interface. The small first slice requires no runtime model credentials and no frontend dependency tree. The data layer and source limitations are explicit so the next iteration can replace curated inputs without rewriting the interaction model.
