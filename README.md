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
| **UI** | Next.js clinical risk console (risk assessment + RAG Q&A) |
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

## Current model metrics

The checked-in artifact is a calibrated MLP, selected on validation after cross-validation
and tuning. The holdout test is used for final evaluation (train/validation/test: 60/20/20).

| Metric | Value |
|--------|-------|
| **Selected model** | MLP (PyTorch training, NumPy inference, calibrated) |
| **Holdout ROC AUC** | 0.82581 |
| **CV ROC AUC** | 0.83049 ± 0.00239 |
| **F1 (validation-selected threshold)** | 0.46543 |
| **Dataset** | `alexteboul/diabetes-health-indicators-dataset` |

Metrics live in [`artifacts/metrics.json`](artifacts/metrics.json). Local training writes
`artifacts/risk_model.joblib`, `metrics.json`, and `model_card.md`.

## Architecture

```text
Patient input (Next.js / API)
        │
        ▼
FastAPI  ──►  BRFSS risk model (local artifact)
        │
        ▼
Orchestrator
   ├── MLP feature explainability (sensitivity; SHAP for linear models)
   ├── Safety guardrails + escalation
   ├── KB/RAG (required Neo4j + bge-m3 embeddings, in-memory vector index)
   ├── ChromaDB memory (similar cases)
   ├── Explanation (OpenAI optional → rule-based fallback)
   ├── Recommendation (OpenAI optional → rule-based fallback)
   └── Q-learning support policy (simulated training; safety rules take precedence)
        │
        ▼
Structured response → UI tabs (Assessment / Evidence / History)
```

The **local demo runs without paid API keys**. Risk scoring, feature drivers, RAG, memory, and safety layers work out of the box; explanation and recommendation use built-in fallbacks when `OPENAI_API_KEY` is unset.

Details: [`docs/architecture.md`](docs/architecture.md)

The Assessment tab also offers source-backed measurement scales and an actionable
follow-up question for missing glucose or measurement context. Answering reruns the
assessment; declining a measurement prevents repeated questions for that profile.
See [`docs/hoi_bo_sung_va_thang_do.md`](docs/hoi_bo_sung_va_thang_do.md).

## Tech stack

- **ML:** scikit-learn, LightGBM, pandas, joblib — local training
- **GPU environment:** PyTorch CUDA, verified on the local RTX 5060 Ti; trains the MLP candidate (optional, inference runs on NumPy without torch)
- **Agents:** ChromaDB, local medical knowledge base; optional OpenAI for richer text (not required)
- **Backend:** FastAPI, Uvicorn, Docker
- **Frontend:** Next.js 15, TypeScript, Tailwind, TanStack Query, Recharts
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
to `data/train/diabetes_binary_health_indicators_BRFSS2015.csv`. Model outputs go to `artifacts/`.
Both default paths are based on the project directory.
Application startup requires a trained model at `MODEL_ARTIFACT_PATH` (default:
`artifacts/risk_model.joblib`). A missing model produces an initialization error;
the application does not train a replacement from demo data.

### 3. Configure environment

```powershell
Copy-Item .env.example .env
Copy-Item web/.env.example web/.env.local
```

Neo4j is required at application startup. Set `NEO4J_PASSWORD` in `.env`, start
`docker compose up -d neo4j`, and load the knowledge base following
[the Neo4j setup guide](docs/neo4j_kb.md). Startup errors do not fall back to JSON;
Load the versioned seed `artifacts/kb_diabet.cypher`; Neo4j is the source of truth for entities,
relations and evidence. `python scripts/collect_corpus.py` refreshes sources and evidence passages from
web/PDF while keeping the curated entities and relations already in Neo4j. Application requests,
RAG evaluation, integration tests and the report notebook all read the processed knowledge from Neo4j.

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

Open **http://localhost:3000**.

### Docker (all services)

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Next.js console | http://localhost:3000 |
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
| `data/train/diabetes_binary_health_indicators_BRFSS2015.csv` | Full training dataset |
| `models/training_pipeline.py` | Training pipeline |
| `artifacts/` | Model, metrics and model card |
| `data/chroma/` | Knowledge index and case memory |
| `data/corpus/sources.json` | Source manifest for refreshing evidence passages in Neo4j |
| `data/eval/rag_retrieval_questions.json` | Labeled RAG evaluation questions |
| Neo4j (`NEO4J_URI`, `NEO4J_DATABASE`) | Processed knowledge for the application, evaluation, integration tests and reports |
| `artifacts/kb_diabet.cypher` | Cypher script to populate or restore the Neo4j knowledge base |
| `logs/` | Decision logs and runtime checks |

See [data/README.md](data/README.md) for the data lifecycle and commands.

## Project structure

```text
healthcare-agent-system/
├── agents/           # Orchestrator, explainer, recommender, retriever
├── api/              # FastAPI app
├── artifacts/        # Local model, metrics.json, model_card.md
├── data/             # corpus/, train/, eval/, ChromaDB
├── models/           # RiskModel + local training pipeline
├── web/              # Next.js production UI
├── infra/aws/        # Terraform (App Runner + ECR)
├── scripts/          # Download data, train, evaluate locally
└── tests/            # Automated tests
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
