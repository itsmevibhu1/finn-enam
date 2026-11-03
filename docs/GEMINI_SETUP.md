# Gemini free-tier setup

1. Open https://aistudio.google.com/apikey and sign in with your Google account.
2. Create a project/key on the free tier. Do not activate Cloud Billing or upgrade the project to paid usage for this prototype.
3. Open the ignored `.env.local` file in the assignment workspace and set `GEMINI_API_KEY` to your key. Keep the existing provider/model values.
4. Tell the coding assistant that the key is saved locally; do not send the key in chat.

The default model is `gemini-3.5-flash-lite`, listed with free input/output tokens on Google's pricing page checked November 3, 2026. Availability and quotas depend on your project and region. The code does not enable billing, cannot verify your account's billing tier from an API key, and never falls back to a paid-only model. Keep your project on the free tier.

## First test

```bash
python3 scripts/model_research.py HCLTECH --question 'What changed in management growth guidance?' --scope earnings --period latest4 --publish-default
```

This retrieves a small set of primary-source passages, requests a structured draft, checks exact quotes and citation IDs, and caches a valid result. It makes at most two generation attempts per uncached question. The application's default cap is eight API attempts per UTC day; Google's own quotas may be lower. A rate-limit error stops generation rather than switching models or purchasing capacity.

Only selected public-company document passages are sent. Google's free-tier pricing states that submitted content can be used to improve its products. No private portfolio holdings, credentials, broker reports, or news commentary are needed for the current mock-portfolio workflow.

The browser does not receive the API key. Do not place it in `dist/`, a frontend JavaScript file, the hosting manifest, or GitHub. Hosted inference will require a server-side secret and endpoint; a static deployment alone does not run this Python integration.

Local-model files remain ignored and unused by default. The local inference server was stopped when the provider choice changed.

Sources:
- https://ai.google.dev/gemini-api/docs/api-key
- https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite
- https://ai.google.dev/api/generate-content

Temporary Gemini HTTP 503 overload receives one retry after two seconds. Each outbound attempt counts against the application cap. Authentication and quota failures are not retried automatically. A model-output validation correction can also require another completion; no paid-model fallback is used.
