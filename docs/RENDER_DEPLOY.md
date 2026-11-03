# Hosted Python deployment

The Render service runs the same UI, Gemini research jobs and primary-PDF collection pipeline as the local server. The separate static Sites publication cannot execute these Python endpoints.

## Deploy from GitHub

1. Sign into https://dashboard.render.com with GitHub.
2. Select **New → Blueprint** and connect the private `itsmevibhu1/finn-enam` repository. If it is missing, grant the Render GitHub app access to this repository.
3. Render reads the root `render.yaml`. Confirm the web service uses the **Free** plan.
4. For `GEMINI_API_KEY`, paste the value from your local ignored `.env.local` into Render's secret field. Do not commit the key, send it through chat, or change your Google project to paid billing.
5. Deploy. Docker installs Poppler and runs the Python server on Render's assigned `PORT`. No Python package installation is needed.
6. Share the actual `https://…onrender.com` service URL after the deployment reports **Live**. Do not assume the service name guarantees a particular URL.

## Acceptance checks

- `/healthz` returns `{"status":"ok"}`.
- `/api/capabilities` reports `on_demand_ingestion:true` and `model_generation:true` when the server key is set. This configuration check alone does not prove successful model authentication.
- Research displays **Draft answer** for indexed companies. Choose HCLTECH, earnings calls, latest four-quarter window, and submit the default question.
- Confirm the draft's primary-source page links and cached repeat.
- Enter a company outside the six prebuilt indexes and choose **Find company documents**. Primary websites may block cloud-hosted downloads; failures must stay visible. An attempted request is not verified company coverage.
- Confirm an external reviewer can open the service URL without your account. The GitHub source repository remains private until explicitly shared or made public.

## Free-plan limits

Render free services sleep after fifteen minutes without traffic; waking takes about a minute. Runtime files are ephemeral: newly collected documents, generated caches, the local request counter and in-memory jobs are lost on restart, redeploy or spin-down. The six bundled indexes survive as deployment assets. The eight-attempt UTC-day application cap is therefore per retained runtime filesystem, not a durable cross-restart billing control. Google's account quota remains the authoritative vendor limit. Keep Google billing disabled if using only the free tier.

Downloads run one at a time on this service to reduce peak memory. Research is separately serialized, jobs are bounded, and identical concurrent research requests share a job. Live collection does not run automatically at startup. Price and filing data remain dated snapshots until refreshed and redeployed; no automatic scheduler is claimed.

Docker builds from the synchronized `finn-site` checkout (the root of the GitHub repository):

```sh
docker build -t finn-enam .
docker run --rm -p 10000:10000 --env-file .env.local -e PORT=10000 finn-enam
```

The image copies an explicit source/data/asset allowlist. `.dockerignore` additionally excludes local credentials, PDFs, model files, caches and Git metadata. The service runs as an unprivileged user. This is a single-process assessment prototype, not a durable multi-tenant research platform.

References: https://render.com/docs/free and https://render.com/docs/blueprint-spec.
