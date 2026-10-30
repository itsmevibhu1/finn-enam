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

The first interactive prototype is implemented. Present now:

- Responsive briefing, research, portfolio, and source-library screens.
- EOD prices and volumes fetched for all 18 mock-portfolio companies; configurable, device-local price/volume thresholds.
- A manually verified Infosys case study with four FY25 calls, annual-report corroboration, and one pending FY27 guidance record.
- Five deterministic comparisons: exceeded earlier guidance, met an intermediate range, missed the latest growth range, met margin guidance, and pending FY27 delivery.
- Source-page links, revision history, evidence export, a historical digest window, and searchable verified summaries.
- A local PDF importer preserving original bytes, a SHA-256 hash, source metadata, and page-level text.
- Automated financial-rule tests and browser interaction/mobile-layout checks.

Important limits: research currently covers INFY only; AI extraction, arbitrary-ticker research, full-document semantic search, automatic refresh, and portfolio-wide exchange filings are not working. Direct Infosys PDF downloads and NSE API/RSS requests returned HTTP 403. The app labels curated evidence and coverage gaps explicitly. No model API calls have been made.

See `docs/PROGRESS_REPORT.md` for measured results and improvement priorities.

## Run the prototype

From the original assignment workspace:

```bash
python3 -m http.server 8000 --directory finn-site/dist
```

From the synchronized Sites source checkout, use `--directory dist` instead. Open `http://localhost:8000`. Serving the app over HTTP is required for its JSON snapshot. No npm install or frontend build is needed.

## Refresh data and rebuild

```bash
python3 scripts/refresh_market.py
python3 scripts/refresh_announcements.py
python3 scripts/build_snapshot.py
python3 -m unittest discover -s tests -v
```

Network collectors can fail independently and record their failures. The snapshot builder remains usable without a successful exchange refresh. Publication is a separate step; reloading the browser does not fetch new market data. `scripts/collect_infosys.py` attempts direct official-document collection and records HTTP failures; it does not supply the curated research facts.

Browser checks use `node scripts/browser_check.mjs` and the installed Chrome path documented inside the script. The original workspace includes an ignored portable Node runtime under `.tools/`; another machine can use its own Node runtime with built-in WebSocket support.

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
