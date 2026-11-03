# Demo evaluation and improvements — November 3, 2026

## Reproducible checks without model calls

Run `python3 scripts/evaluate_demo.py`. Inputs and per-case results are committed.

| Check | Result | What it establishes |
| --- | --- | --- |
| Five inspected company questions | 5/5 expected source passages retrieved | The bounded evidence pack includes the inspected primary page; generated answers are a separate check. |
| Missing-quarter, unknown-term and generic-document questions | 3/3 evidence gaps | These questions do not acquire unrelated evidence. |
| Twenty captured NSE description labels | 15/20 before tuning; 20/20 after | Regression behavior on a small calibration set, not out-of-sample classification accuracy. |
| Similar-name issuer exclusions | 3/3 | Slone Infosystems, Reliance Mutual Fund and HDFC AMC do not match the corresponding portfolio issuers. |
| Five curated Infosys comparisons | 5/5 expected verdicts reproduced | Consistency of the deterministic historical case, not automatic extraction accuracy. |

The announcement sample is twenty consecutive records from a captured official NSE RSS response, including issuers outside the portfolio. Labels were assigned from the description, not by reading every attachment. Ambiguous recordings remain unclassified unless call identity is explicit. This sample does not establish complete feed coverage or materiality accuracy.

## Live generated examples

`HOSTED_DEMO_RESULTS.json` records the actual serial API run on the deployed research-v3 pipeline.

| Company | Observed outcome | Model-generation latency |
| --- | --- | --- |
| HCLTECH | Checked draft, two observations | 61.95 seconds |
| DIXON | Checked draft, three observations | 47.89 seconds |
| PERSISTENT | Rejected after both drafts failed exact-quote checks | Not published |
| COFORGE | Checked draft, two observations | 23.43 seconds |
| ASTRAL | Application request cap reached | No draft generated in this run |

Three successful generated examples, one validation rejection and one cap block are not a five-company accuracy score. Successful source references and quotes were mechanically checked against their primary documents. Their short interpretations remain drafts; for example, temporal wording such as describing FY27 as “upcoming” needs human review. No annual promise is automatically assessed against an incomparable quarterly outcome.

The three successful answers are retained in `data/demo_answers.json` as a bundled cache. Reuse requires an exact question/filter/model/prompt/pipeline/corpus cache key. Quotes are rechecked and source metadata rebuilt from the corpus before serving. This preserves useful cache entries across a free-host restart without claiming a new live generation. A changed corpus misses this cache. New questions continue through the normal bounded model path.

## Improvements made

- Removed generic document-wrapper words and used inverse-frequency keyword ranking, preventing an annual-report cover from beating working-capital evidence.
- Kept financial results distinct from call recordings. Generic recording notices retain an unknown state instead of an assumed earnings identity.
- Added a bounded overload retry, with each attempt counted against the runtime cap.
- Extended short checked quotes in the browser with up to twenty-five actual source words, so nearby figures are visible without asking the model to generate them. Exports retain both the model's checked quote and displayed source excerpt.
- Preserved three actual generated drafts in a corpus-bound cache rather than repeatedly spending free-tier requests after restarts.
- Exported the actual available build conversation, redacted credential material, and checked its provenance hash before publishing.

## Highest-value next work

1. Make the model select precomputed source-span IDs rather than retyping quotes; retain the same strict source check. This targets the observed Persistent rejection.
2. Reduce cold-generation latency and measure a larger independent set of questions, including speaker attribution, financial scope and temporal wording.
3. Add durable cache/job state and scheduled market/filing ingestion. The runtime request counter is currently ephemeral; Google's account quota remains authoritative.
4. Broaden primary-document coverage and close explicit earnings-quarter gaps without treating investor events as quarterly calls.

The implementation intentionally favors inspected evidence and visible failures over claims of comprehensive autonomous financial analysis.

## Final deployment checks

The final source revision `7d7bfe1` was confirmed live. All three successful demo questions returned `cache_source=bundled_verified_demo` after deployment, verifying that their cache survived without new model calls. Thirty-one checks passed against the actual public HTTPS service, including the research endpoint, cached repeat, primary page links, the displayed guidance range and four mobile views. Seventy-three Python tests and the JavaScript suites passed. The GitHub repository and redacted conversation were also fetched without authentication and returned HTTP 200.
