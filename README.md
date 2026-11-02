# Healthcare AI Risk Console

Local healthcare AI prototype: **model training**, **multi-agent orchestration**, **FastAPI inference**, and a **Next.js dashboard**.

> **Educational prototype only — not medical advice.** Not a medical device. Not clinically validated.

**Repository:** [github.com/adit24dhaya/healthcare-agent-system](https://github.com/adit24dhaya/healthcare-agent-system)

## Local services

| | URL |
|---|-----|
| **Web app (Next.js)** | http://localhost:3000 |
| **API docs (FastAPI)** | http://localhost:8000/docs |
| **API health** | http://localhost:8000/health |

## What this demonstrates

| Layer | What you built |
|-------|----------------|
| **Data & ML** | CDC BRFSS diabetes dataset (253k rows), local training, CV + tuning + calibration |
| **Inference** | FastAPI service with persisted `joblib` artifact and BRFSS feature mapping |
| **AI agents** | Risk scoring, SHAP/sensitivity explainability, RAG retrieval, memory, safety guardrails; optional LLM text |
| **UI** | Next.js clinical risk console (portfolio UI) + Streamlit for rapid iteration |
| **Runtime** | Local Python and Node.js; Docker Compose for local services |

## Product demo

Portfolio screenshots and short browser recordings are saved in [`docs/media`](docs/media/).

| Assessment | Evidence |
|------------|----------|
| ![Assessment dashboard with risk gauge and feature impact chart](docs/media/screenshots/assessment.png) | ![Evidence tab with retrieved clinical context and similar cases](docs/media/screenshots/evidence.png) |

| History | Missing glucose safety flow |
|---------|-----------------------------|
| ![History tab with risk distribution and memory records](docs/media/screenshots/history.png) | ![Missing glucose state with reduced confidence warning](docs/media/screenshots/missing-glucose.png) |

Scenario screenshots with varied patient values, health profile inputs, and lifestyle/access inputs:

| Preventive profile | Cardiometabolic profile | Access/lab uncertainty profile |
|--------------------|-------------------------|--------------------------------|
| ![Preventive profile with expanded health and lifestyle sections](docs/media/screenshots/scenario-preventive-profile.png) | ![Cardiometabolic risk profile with expanded health and lifestyle sections](docs/media/screenshots/scenario-cardiometabolic-profile.png) | ![Access barrier and missing glucose profile with expanded health and lifestyle sections](docs/media/screenshots/scenario-access-lifestyle-profile.png) |

Short clips:

- [Patient assessment flow](docs/media/videos/01-assessment-flow.webm)
- [Retrieved evidence and similar cases](docs/media/videos/02-evidence-flow.webm)
- [Risk history and memory records](docs/media/videos/03-history-flow.webm)
- [Missing glucose safety behavior](docs/media/videos/04-missing-glucose-flow.webm)

## Reference baseline metrics

These checked-in metrics describe the previous baseline run. The evaluation protocol
will be corrected in Step 3 before generating new results.

| Metric | Value |
|--------|-------|
| **Selected model** | Histogram gradient boosting (calibrated) |
| **Holdout ROC AUC** | 0.827 |
| **CV ROC AUC** | 0.831 ± 0.002 |
| **F1 (tuned threshold)** | 0.469 |
| **Dataset** | `alexteboul/diabetes-health-indicators-dataset` |

Metrics live in [`artifacts/metrics.json`](artifacts/metrics.json). Local training writes
`artifacts/risk_model.joblib`, `metrics.json`, and `model_card.md`.

## Architecture

```text
Patient input (Next.js / Streamlit / API)
        │
        ▼
FastAPI  ──►  BRFSS risk model (local artifact)
        │
        ▼
Orchestrator
   ├── Feature explainability (SHAP or sensitivity)
   ├── Safety guardrails + escalation
   ├── RAG medical context retrieval
   ├── ChromaDB memory (similar cases)
   ├── Explanation (OpenAI optional → rule-based fallback)
   └── Recommendation (OpenAI optional → rule-based fallback)
        │
        ▼
Structured response → UI tabs (Assessment / Evidence / History)
```

The **local demo runs without paid API keys**. Risk scoring, feature drivers, RAG, memory, and safety layers work out of the box; explanation and recommendation use built-in fallbacks when `OPENAI_API_KEY` is unset.

Details: [`docs/architecture.md`](docs/architecture.md)

## Tech stack

- **ML:** scikit-learn, LightGBM, pandas, joblib — local training
- **GPU environment:** PyTorch CUDA, verified on the local RTX 5060 Ti; trains the MLP candidate (optional, inference runs on NumPy without torch)
- **Agents:** ChromaDB, local medical knowledge base; optional OpenAI for richer text (not required)
- **Backend:** FastAPI, Uvicorn, Docker
- **Frontend:** Next.js 15, TypeScript, Tailwind, TanStack Query, Recharts; Streamlit
- **Deploy:** Vercel, Heroku, Docker; optional AWS App Runner + Terraform

## Local setup (PowerShell)

### 1. Install dependencies

Use Python 3.11 in `.venv` and Node.js 22 or later. The existing environment from Step 2 can be reused.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-cuda.txt
```

### 2. Prepare local data and train

```powershell
.\.venv\Scripts\python.exe scripts/download_training_data.py
.\.venv\Scripts\python.exe scripts/train_diabetes_model.py
```

The dataset is downloaded from the [UCI BRFSS mirror](https://archive.ics.uci.edu/dataset/891/cdc+diabetes+health+indicators)
to `data/diabetes_binary_health_indicators_BRFSS2015.csv`. Model outputs go to `artifacts/`.
Both default paths are based on the project directory.

### 3. Configure environment

```powershell
Copy-Item .env.example .env
Copy-Item web/.env.example web/.env.local
```

### 4. Run API + Next.js UI

**Terminal 1 — API:**

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.app:app --reload --env-file .env
```

**Terminal 2 — Web UI:**

```powershell
cd web
npm ci
npm run dev
```

Open **http://localhost:3000** (production portfolio UI) or **http://localhost:8501** with `streamlit run ui/app.py`.

### Docker (all services)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Next.js console | http://localhost:3000 |
| Streamlit | http://localhost:8501 |
| FastAPI | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health`, `GET /v1/health` | Health check |
| `POST /predict`, `POST /v1/predict` | Full multi-agent analysis |
| `POST /predict/summary`, `POST /v1/predict/summary` | Condensed triage output |
| `GET /history` | Recent memory records |

Example:

```bash
curl -s http://127.0.0.1:8000/health
```

Optional auth: `REQUIRE_API_TOKEN=true` and `Authorization: Bearer <API_TOKEN>`.

## Local paths

| Path | Contents |
|------|----------|
| `data/diabetes_binary_health_indicators_BRFSS2015.csv` | Full training dataset |
| `models/training_pipeline.py` | Training pipeline |
| `artifacts/` | Model, metrics and model card |
| `data/chroma/` | Knowledge index and case memory |
| `data/kb/diabetes_kb.json` | Source file of the Neo4j knowledge graph ([docs/neo4j_kb.md](docs/neo4j_kb.md)) |
| `logs/` | Decision logs and runtime checks |

## Project structure

```text
healthcare-agent-system/
├── agents/           # Orchestrator, explainer, recommender, retriever
├── api/              # FastAPI app
├── artifacts/        # Local model, metrics.json, model_card.md
├── data/             # Local training CSV, knowledge base, memory
├── models/           # RiskModel + local training pipeline
├── web/              # Next.js production UI
├── ui/               # Streamlit dashboard
├── infra/aws/        # Terraform (App Runner + ECR)
├── scripts/          # Download data, train, evaluate locally
└── tests/
```

## Development

```bash
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/pytest -q

cd web && npm run lint && npm run typecheck && npm run build
```

## Security & disclaimer

- See [`docs/security.md`](docs/security.md) for PII and hardening notes.
- Decision audit log: `logs/decisions.jsonl`
- This system must not be used as the sole basis for clinical decisions.

## License

MIT or Apache-2.0 — choose before public release.
