# AI Interviewer

A personal AI interview coach for software-engineering placement prep. Conducts
adaptive technical, HR, project, and resume-based interviews; remembers your
history; detects recurring weaknesses; and gets better at interviewing you
over time.

This is a portfolio project built incrementally, milestone by milestone. See
[Status](#status) for what's actually built vs. planned.

## Status

**Milestone 1 — Foundation: in progress.**

- [x] Repository structure
- [x] FastAPI backend with MongoDB (Motor) connection + `/api/health`
- [x] Next.js + TypeScript + Tailwind frontend scaffold
- [ ] Minimal dashboard wired to the health endpoint
- [ ] Verified end-to-end (frontend → backend → database)

Nothing beyond Milestone 1 (interview engine, AI evaluation, resume parsing,
etc.) is implemented yet — see `docs/` for the full roadmap as it's added.

## Architecture

A **modular monolith**, not microservices:

- **Frontend** — Next.js (App Router) + TypeScript + Tailwind CSS
- **Backend** — Python + FastAPI + Pydantic, organized by responsibility
  (`api/`, `core/`, `db/`, `models/`, `schemas/`, `services/`, `ai/`,
  `interview/`, `rag/`, `utils/`) rather than by technical layer
- **Database** — MongoDB (local `mongod` for development; Atlas for
  production / Vector Search later)
- **AI** — Anthropic Claude API, called from dedicated backend components
  (question generation, answer evaluation, follow-ups, etc.) rather than one
  giant prompt

```
ai-interviewer/
├── frontend/     Next.js app
├── backend/      FastAPI app
│   ├── app/
│   │   ├── api/routes/   HTTP endpoints
│   │   ├── core/         config/settings
│   │   ├── db/           MongoDB connection
│   │   ├── models/       DB document models        (Milestone 2+)
│   │   ├── schemas/      Pydantic request/response  (Milestone 2+)
│   │   ├── services/     business logic             (Milestone 2+)
│   │   ├── ai/           LLM client + components     (Milestone 2+)
│   │   ├── interview/    interview state machine     (Milestone 2+)
│   │   └── rag/          retrieval/embeddings        (later)
│   └── tests/
├── prompts/      versioned LLM prompts (interviewer/evaluator/followup/report)
├── docs/
└── scripts/
```

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Database | MongoDB (Motor async driver) |
| AI | Anthropic Claude API |

## Setup

### Prerequisites

- Node.js 20+ and npm
- Python 3.12
- MongoDB running locally (`mongod` as a service, or `docker run -p 27017:27017 mongo`)

### Backend

```bash
cd backend
python -m venv venv
./venv/Scripts/activate        # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env           # then fill in ANTHROPIC_API_KEY etc.
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/api/health — should return
`{"status":"ok","database":"connected",...}` when MongoDB is reachable.
Interactive API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points the frontend at the backend URL
npm run dev
```

Visit http://localhost:3000

### Tests

```bash
cd backend
pytest -v
```

## Environment variables

See [`backend/.env.example`](backend/.env.example) for the full list. Never
commit a real `.env` file — it's git-ignored.

## Roadmap

Following the milestone plan from the product spec:

1. **Foundation** — repo, frontend/backend/DB wiring, health check *(in progress)*
2. **Interview MVP** — setup → question → answer → evaluation → next question
3. **Persistence** — interview history, reports
4. **Resume ingestion** — upload, extraction, resume-based questions
5. **Adaptive interviewing** — difficulty adaptation, follow-ups, weak-topic detection
6. **Analytics** — progress tracking, recurring weaknesses, prep plans
7. **Job/Company mode** — JD analysis, role-specific interviews
8. **Voice interviews** — STT/TTS, live interview UI
9. **Production hardening** — auth, security, logging, deployment

## License

Personal project — not currently licensed for reuse.
