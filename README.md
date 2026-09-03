# AI Interviewer

A personal AI interview coach for software-engineering placement prep. Conducts
adaptive technical, HR, project, and resume-based interviews; remembers your
history; detects recurring weaknesses; and gets better at interviewing you
over time.

This is a portfolio project built incrementally, milestone by milestone. See
[Status](#status) for what's actually built vs. planned.

## Status

**Milestones 1 (Foundation), 2 (Interview MVP), and 5 (Adaptive Engine): complete.**
Milestones 3/4/6-9 not started - see Roadmap. (5 was pulled forward, ahead
of 3/4, at the user's request - it doesn't depend on persistence/resume.)

- [x] Repository structure, FastAPI + MongoDB + Next.js, `/api/health`
- [x] Technical Interview: setup → question → answer → evaluation → next
      question/follow-up → completion, fully working end-to-end
- [x] Interview state machine (`app/interview/state_machine.py`) - now
      includes the FOLLOW_UP branch, persisted to MongoDB (`interviews`,
      `interview_questions`, `answers`, `evaluations` collections)
- [x] **Adaptive engine** (spec §8), entirely deterministic application
      logic, not LLM-driven:
  - `difficulty_controller.py` - difficulty moves at most one step
    (easy/medium/hard) per answer, based on the evaluation's numeric score
  - follow-up branching in `engine.py` - a vague or evaluator-flagged
    answer gets a same-topic "why/how" deep-dive question instead of moving
    on, capped at one follow-up in a row
  - `weakness_tracker.py` + `engine.select_next_topic()` - a topic with 2+
    below-threshold answers in this session gets targeted with the next
    question instead of strict round-robin
- [x] AI layer behind an interface (`app/ai/base.py`, now including
      `generate_follow_up_question`): a deterministic `StubLLMClient` (used
      automatically without an API key, and what all adaptive-engine tests
      run against) and an `AnthropicLLMClient` (implemented against the
      current Anthropic SDK, **not yet verified against a live key** - see
      Known limitations)
- [x] Deterministic vague-answer detection (spec §12)

Not yet implemented: HR/project/resume interview modes, candidate profile,
cross-interview weakness detection, analytics, voice, auth. See Roadmap.

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
│   ├── app/
│   │   ├── page.tsx                     dashboard
│   │   └── interview/
│   │       ├── new/page.tsx             setup form
│   │       └── [id]/                    live interview + report
│   └── lib/api.ts                       typed fetch wrapper (mirrors backend schemas)
│
├── backend/      FastAPI app
│   ├── app/
│   │   ├── api/routes/     HTTP endpoints (health, interviews)
│   │   ├── core/           config/settings
│   │   ├── db/             MongoDB connection
│   │   ├── schemas/        Pydantic request/response + LLM structured output
│   │   ├── interview/      state machine, engine (orchestrator), Mongo repository,
│   │   │                   vague-answer detector, difficulty_controller,
│   │   │                   weakness_tracker (all deterministic, unit tested)
│   │   ├── ai/             LLMClient interface, stub + Anthropic implementations,
│   │   │                   prompt loader
│   │   ├── models/         (unused so far - schemas/ doubles as the DB shape)
│   │   ├── services/       (unused so far - logic lives in interview/ for now)
│   │   └── rag/            retrieval/embeddings                    (later)
│   └── tests/
│
├── prompts/      versioned LLM prompt templates (interviewer/, evaluator/, ...)
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

### Try it

1. Open http://localhost:3000, click **Start Interview**
2. Pick topics/difficulty/question count, start
3. Answer each question - you'll see per-answer scores and feedback. Try a
   deliberately vague answer ("because it's scalable") to see a same-topic
   follow-up question fire, and a strong detailed answer to see the
   difficulty (shown top-right) step up
4. After the last question, view the full report

Without `ANTHROPIC_API_KEY` set, this all runs against a deterministic stub
AI (canned questions, heuristic scoring) - useful for developing/testing the
app itself, but not a real interviewer. Set the key to get real questions
and evaluation.

## Environment variables

See [`backend/.env.example`](backend/.env.example) for the full list. Never
commit a real `.env` file — it's git-ignored.

## Known limitations

- **`AnthropicLLMClient` is implemented but unverified against a live API
  key** in this environment - it's written against the current documented
  SDK API and type-checks, but no live model call has actually been made.
  Set `ANTHROPIC_API_KEY` and run a real interview to confirm before relying
  on it.
- **Single technical-interview mode only** - no HR/project/resume/JD modes
  yet.
- **Adaptive engine is session-only** - weak-topic targeting and difficulty
  adaptation only see the current interview. Detecting weaknesses that
  *recur across* interviews (spec §15) needs the candidate-profile/history
  infrastructure from Milestones 3/6, not built yet.
- **Follow-ups cap at 1 in a row** (`MAX_CONSECUTIVE_FOLLOW_UPS` in
  `engine.py`) - a deliberate choice to keep interview length predictable
  against the question-count budget you set at setup, at the cost of not
  chaining a longer "why, why, why" probe on a single answer.
- **Single user, no auth** - every interview is stored under a fixed
  `user_id`. Fine for personal use now; real auth is Milestone 9.
- **No interview history list UI yet** - individual reports work
  (`/interview/[id]/report`), but there's no dashboard view of past
  interviews (Milestone 3/16).

## Roadmap

Following the milestone plan from the product spec:

1. **Foundation** — repo, frontend/backend/DB wiring, health check *(done)*
2. **Interview MVP** — setup → question → answer → evaluation → next question *(done)*
3. **Persistence** — interview history *list UI* (individual reports + all
   underlying data already exist as of Milestone 2)
4. **Resume ingestion** — upload, extraction, resume-based questions
5. **Adaptive interviewing** — difficulty adaptation, follow-ups, weak-topic detection *(done - within a single session; see Known limitations)*
6. **Analytics** — progress tracking, *cross-interview* recurring weaknesses, prep plans
7. **Job/Company mode** — JD analysis, role-specific interviews
8. **Voice interviews** — STT/TTS, live interview UI
9. **Production hardening** — auth, security, logging, deployment

## License

Personal project — not currently licensed for reuse.
