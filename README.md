# FINN

A mobile-first investment research assistant for the ENAM AI Engineer Build Challenge.

**Product question:** What changed, why does it matter, and where is the evidence?

## First milestone

Make one company work end to end before expanding: import primary documents, preserve page-level evidence, compare an earlier management statement with a later reported outcome, and present the comparison on a phone.

Start with INFY because its investor-relations archive is an initial source candidate for results and earnings-call transcripts. Verify document availability and comparability before committing to any particular research finding. The engine must accept other tickers; the portfolio is configuration, not a hard-coded research boundary.

## Planned product

1. **Attention inbox:** a portfolio digest with a selectable window, material events ranked first, routine filings collapsed, related documents grouped, and configurable EOD price/volume thresholds.
2. **Promise tracker:** earlier guidance beside subsequent results, with matched metrics and periods, source evidence, and an explicit unassessable state.

Both workflows will distinguish source facts, computed values, and AI interpretation. Historical replay will be labelled with its date. Never present sample data as live data.

## Repository status

The working prototype is implemented, with further local improvements awaiting publication. Present now:

- Responsive briefing, research, portfolio, and source-library screens.
- EOD prices and volumes fetched for all 18 mock-portfolio companies; configurable, device-local price/volume thresholds.
- A manually verified Infosys case study with four FY25 calls, annual-report corroboration, and one pending FY27 guidance record.
- Five deterministic comparisons: exceeded earlier guidance, met an intermediate range, missed the latest growth range, met margin guidance, and pending FY27 delivery.
- Source-page links, revision history, evidence export, a historical digest window, and searchable verified summaries.
- A reusable ticker pipeline that discovers primary-document links through Screener, downloads exchange/company PDFs, validates basic document identity, and retains page-level text.
- 35 usable PDFs across INFY, HCLTECH, PERSISTENT, DIXON, ASTRAL, and COFORGE: 3,144 PDF pages. Audio notices and failed links are excluded from the search corpus. Five companies have four consecutive earnings quarters indexed; Astral's Q4 FY2026 gap remains explicit.
- Browser-based keyword retrieval over those primary PDFs, one short passage per matching document, with PDF-page links, document hashes, and an exportable evidence pack.
- Corrected NSE RSS ingestion with persistent observed-filings history, category filters, priority rules, routine-item collapsing, and attachment grouping. The first successful morning snapshot had zero matched portfolio filings; it is not a full historical archive.
- A local server that can index an unfamiliar ticker on demand, with bounded jobs and visible status.
- A local PDF importer preserving original bytes, a SHA-256 hash, source metadata, and page-level text.
- Automated financial-rule tests and browser interaction/mobile-layout checks.

Important limits: curated promise comparisons cover INFY only. Gemini research is connected to the local interface through bounded background jobs. The hosted static site does not yet expose model generation. There is no semantic/vector retrieval, automatic scheduling, or complete filing history. The hosted site searches prebuilt corpora; new-ticker downloads run through the local server/CLI. Direct Infosys downloads returned HTTP 403, but exchange-hosted copies were successfully imported. The NSE API remains blocked; RSS works after fixing its date format and issuer matching. The latest successful local price refresh includes November 3 for all 18 companies. Availability and freshness are checked separately. A live Gemini request has produced a draft with source quotes validated against the indexed passages.

## Hosted model API setup

The active provider choice is now Gemini's free tier, replacing the local-model experiment. See [Gemini setup](docs/GEMINI_SETUP.md). Put your own key in the ignored `.env.local` file. The adapter uses a free-tier-eligible model, cached drafts, bounded requests, checked source quotes, and no paid-model fallback. The configured API key has been verified with a live research request. Other users must supply their own key. The application cannot determine your Google project's billing tier from the key; keep that project on the free tier.

See `docs/ITERATION_2_REPORT.md` for the earlier deployed results and `docs/PROGRESS_REPORT.md` for the first iteration.

## Hosted backend

Deploy the Python UI/API service with the included free-plan `render.yaml` and Dockerfile. See [Render deployment](docs/RENDER_DEPLOY.md). Configure `GEMINI_API_KEY` in Render, never in the repository. Free instances sleep on inactivity and discard runtime documents, jobs and caches on restart; bundled indexes remain available. A successful cloud deployment and its public URL must be verified separately.

## Run the prototype

From the original assignment workspace:

```bash
python3 -m http.server 8000 --directory finn-site/dist
```

From the synchronized Sites source checkout, use `--directory dist` instead. Open `http://localhost:8000`. Serving the app over HTTP is required for its JSON snapshot. No npm install or frontend build is needed.

For local on-demand research, use this server instead of the static server:

```bash
python3 scripts/serve.py --port 8000
```

Open `http://127.0.0.1:8000`. With `.env.local` configured, Research offers **Draft answer** for indexed companies. Drafts run in the background, preserve source-page citations, and use a validated cache for repeated questions. The key stays on the server. Enter an unindexed ticker in Research and choose **Find company documents**. This downloads primary files and rebuilds the local index. The server binds to loopback only; the private hosted snapshot does not expose the collection endpoint.

To index any NSE ticker from the command line:

```bash
python3 scripts/research_pipeline.py COFORGE
python3 scripts/build_snapshot.py
```

Screener is only a document-link directory. Its tables, AI summaries, news, and commentary do not enter the research corpus. Discovery candidates and retrieval matches are not automatically verified financial claims. The latest four directory entries may include media calls or investor events; the corpus marks those separately instead of assuming four quarterly earnings calls.

## Refresh data and rebuild

```bash
python3 scripts/refresh_market.py
python3 scripts/refresh_announcements.py
python3 scripts/build_snapshot.py
python3 -m unittest discover -s tests -v
```

Network collectors can fail independently and record their failures. The snapshot builder remains usable without a successful exchange refresh. Publication is a separate step; reloading the browser does not fetch new market data. `scripts/collect_infosys.py` is the original direct-download attempt; prefer the generic `research_pipeline.py` for exchange-hosted copies. A source checkout includes generated corpora and excludes raw PDFs; recollect a ticker to rebuild from its original documents. Existing corpora are retained when their raw PDFs are not downloaded locally.

Browser checks use `node scripts/browser_check.mjs` and the installed Chrome path documented inside the script. The original workspace includes an ignored portable Node runtime under `.tools/`; another machine can use its own Node runtime with built-in WebSocket support.

Retrieval and filing-rule tests also run with `node tests/retrieval.test.mjs` and `node tests/filings.test.mjs`.

## Import a downloaded primary document

Requires Python 3.11+ and the `pdftotext` executable from Poppler. No Python dependencies or model credentials are needed for this step.

```bash
python3 scripts/import_document.py /path/to/report.pdf \
  --ticker INFY \
  --kind annual_report \
  --source-url 'https://company.example/investors/report.pdf' \
  --period FY2026
```

Use the actual document URL and reporting period. Valid kinds are `annual_report`, `transcript`, and `results`. Imported documents live under `data/documents/` and are excluded from version control. The importer does not verify publisher identity or financial claims; those are separate checks.

## Submission

Deadline: November 1, 2026; no time or timezone specified in the brief.

- Working prototype link accessible on a phone.
- GitHub repository with setup and architecture instructions.
- Actual coding-agent/LLM conversation exports or share links.
- Covering email describing decisions, trade-offs, omissions, and next steps.

Send to `assessment@enam.com`, subject `ENAM - IIT screening - 2027`.

Preserve actual AI build conversations from the beginning. A hand-written development log is useful context but does not replace the requested conversation history. Do not include credentials in exports or commits.
