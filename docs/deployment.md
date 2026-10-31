# Production deployment (Vercel + Heroku)

Educational prototype hosting used for the live demo. Not medical advice.

## Architecture

```text
Browser → Vercel (Next.js, web/) → server routes proxy → Heroku (FastAPI + joblib model)
```

## Live URLs

| Service | URL |
|---------|-----|
| Web UI | https://healthcare-agent-system-teal.vercel.app |
| API docs | https://healthcare-achv-api-adit24-cbf3793610ff.herokuapp.com/docs |
| Health | https://healthcare-achv-api-adit24-cbf3793610ff.herokuapp.com/health |

## Vercel (frontend)

1. Import `adit24dhaya/healthcare-agent-system` from GitHub.
2. **Root Directory:** `web`
3. **Framework:** Next.js
4. Environment variables (Production and Preview):

| Name | Value |
|------|--------|
| `API_BASE_URL` | `https://healthcare-achv-api-adit24-cbf3793610ff.herokuapp.com` (no trailing slash) |
| `API_TOKEN` | Same as Heroku `API_TOKEN` |

5. Deploy. Redeploy after changing env vars.

## Heroku (API)

- App: `healthcare-achv-api-adit24`
- Stack: `heroku/python` (see repo `Procfile`, `runtime.txt`)
- Config: `REQUIRE_API_TOKEN=true`, `API_TOKEN`, `MODEL_ARTIFACT_PATH=artifacts/risk_model.joblib`, `LOG_DIR=logs`
- **Not required:** `OPENAI_API_KEY` — production uses rule-based explanation and recommendation when unset

The production model artifact is bundled in the Heroku slug (not in GitHub). To redeploy API changes with the model:

```bash
git checkout -b heroku-deploy
git add -f artifacts/risk_model.joblib   # after local training
git commit -m "Update model artifact for Heroku"
git push heroku heroku-deploy:main
git checkout main && git branch -D heroku-deploy
```

Code-only API updates without re-bundling the model:

```bash
git push heroku main:main
```

(Only works if `main` includes the model commit on Heroku’s branch history.)

## Cost notes

- **Vercel Hobby:** sufficient for this UI.
- **Heroku:** one web dyno; GitHub Student Pack provides ~$13/month platform credit for 24 months.
- Do not add extra Heroku services unless needed.

## Security

- Never commit `API_TOKEN` or `OPENAI_API_KEY`.
- Production uses `REQUIRE_API_TOKEN=true`; Vercel holds the token server-side in API route proxies.
