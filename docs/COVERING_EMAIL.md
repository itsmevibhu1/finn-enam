To: assessment@enam.com

Subject: ENAM - IIT screening - 2027

Dear ENAM team,

Please find my FINN prototype:

- Working prototype: https://finn-enam-l5x9.onrender.com
- Repository: https://github.com/itsmevibhu1/finn-enam
- Actual AI build conversation, with credentials redacted: https://github.com/itsmevibhu1/finn-enam/blob/main/docs/AI_BUILD_HISTORY.md
- Short demo guide: https://github.com/itsmevibhu1/finn-enam/blob/main/docs/DEMO_GUIDE.md

I focused on two workflows: an attention inbox for an eighteen-company mock portfolio, and primary-source research that connects management statements to inspectable evidence. A historical Infosys case shows how the same outcome can exceed earlier guidance but miss the final revision. Research also supports other companies through generic document discovery and ingestion.

Financial comparison verdicts are calculated in code. Gemini supplies concise interpretations from retrieved company/exchange documents; exact quotations and source references are checked before a draft is shown. Content hashes, bounded retrieval, request limits and caching keep model use small.

I deliberately left out broad investment recommendations and a full suite of financial dashboards. Current limits include incomplete transcript windows for some companies, a rolling filing archive, dated price snapshots, and ephemeral free-host runtime storage. Next I would add durable ingestion/scheduling and evaluate financial extraction against a larger independently labelled dataset.

Setup, trade-offs, calibration results and the demo walkthrough are documented in the repository. The free host may take about a minute to wake after inactivity.

Regards,
Vibhu
