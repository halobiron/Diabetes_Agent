# Healthcare AI Risk Console Web UI

Next.js production frontend for the healthcare risk API.

## Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- TanStack Query
- Recharts
- Lucide icons

## Local Run

Start FastAPI from the repo root:

```bash
.venv/bin/uvicorn api.app:app --reload
```

Start the web app:

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3000`.

The web app calls its own `/api/predict` route, which forwards requests to FastAPI
using `API_BASE_URL` and optional `API_TOKEN`. This keeps production API credentials
out of browser JavaScript.

## Environment

```bash
API_BASE_URL=http://127.0.0.1:8000
API_TOKEN=
```

## Production Build

```bash
npm run typecheck
npm run build
```
