# AI Interviewer

A personal AI interview coach for software-engineering placement prep. Conducts
adaptive technical, HR, project, and resume-based interviews; remembers your
history; detects recurring weaknesses; and gets better at interviewing you
over time.

This is a portfolio project built incrementally, milestone by milestone. See
[Status](#status) for what's actually built vs. planned.

## Status

**Milestones 1 (Foundation), 2 (Interview MVP), 4 (Resume Ingestion), and 5
(Adaptive Engine): complete.** Milestones 3/6-9 not started - see Roadmap.
(4 and 5 were done out of the spec's numeric order, at the user's request -
neither depends on Milestone 3.)

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
      `generate_follow_up_question` and `extract_candidate_profile`): a
      deterministic `StubLLMClient` (used automatically without an API key,
      and what all adaptive-engine tests run against), an `AnthropicLLMClient`
      (**not yet verified against a live key**), and an `OpenRouterLLMClient`
      (real, **verified working against the live OpenRouter API** - see
      "OpenRouter" below and Known limitations)
- [x] **Multi-provider LLM configuration** - `LLM_PROVIDER` env var
      (`auto`/`stub`/`anthropic`/`openrouter`) selects which client
      `app/ai/factory.py` builds; forced non-`auto` values fail loudly at
      startup if their key is missing, rather than silently using the stub
- [x] Deterministic vague-answer detection (spec §12)
- [x] **Resume ingestion** (spec §6), built as a foundation for future
      personalization, not wired into question generation yet:
  - PDF upload → deterministic text extraction (`pypdf`, no LLM) →
    deterministic tech-keyword matching (`app/resume/keyword_extractor.py`,
    no LLM) → LLM-assisted structuring of education/projects/experience/
    certifications/achievements → merged into one `CandidateProfile`
  - File-type (magic bytes, not just declared content-type) and size
    validation; corrupt/encrypted/image-only PDFs fail gracefully
    (`status: "failed"` with a generic message, not a 500)
  - Modular extractor interface (`app/resume/extractors/`) so DOCX support
    is a new file + one registry line, not a rewrite
  - `raw_text` and structured fields stored as siblings specifically so a
    future RAG/chunking pipeline can use both without reshaping data
    (RAG itself is not implemented)

Not yet implemented: resume-based question generation, HR/project/JD
interview modes, interview-performance candidate profile, cross-interview
weakness detection, analytics, voice, auth, RAG. See Roadmap.

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
│   │   ├── api/routes/     HTTP endpoints (health, interviews, resumes)
│   │   ├── core/           config/settings
│   │   ├── db/             MongoDB connection
│   │   ├── schemas/        Pydantic request/response + LLM structured output
│   │   │                   (interview.py, resume.py)
│   │   ├── interview/      state machine, engine (orchestrator), Mongo repository,
│   │   │                   vague-answer detector, difficulty_controller,
│   │   │                   weakness_tracker (all deterministic, unit tested)
│   │   ├── resume/         upload validation, extractors/ (pypdf, DOCX-ready),
│   │   │                   keyword_extractor (deterministic tech matching),
│   │   │                   profile_merger, service (orchestrator), repository
│   │   ├── ai/             LLMClient interface, stub + Anthropic + OpenRouter
│   │   │                   implementations, factory (provider selection),
│   │   │                   errors (provider-agnostic exception types),
│   │   │                   stub_resume_extractor, prompt loader/builder
│   │   ├── models/         (unused so far - schemas/ doubles as the DB shape)
│   │   ├── services/       (unused so far - logic lives in interview/ and resume/)
│   │   └── rag/            retrieval/embeddings                    (later)
│   └── tests/
│
├── prompts/      versioned LLM prompt templates (interviewer/, evaluator/,
│                 followup/, resume/)
├── docs/
└── scripts/
```

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness + DB connectivity |
| POST | `/api/interviews` | start a technical interview |
| GET | `/api/interviews/{id}` | current state + question |
| POST | `/api/interviews/{id}/answer` | submit an answer, get evaluation + next question |
| GET | `/api/interviews/{id}/report` | full report after completion |
| POST | `/api/resumes` | upload a resume (multipart, PDF only) |
| GET | `/api/resumes` | list uploaded resumes (summary) |
| GET | `/api/resumes/{id}` | resume detail + structured profile |
| DELETE | `/api/resumes/{id}` | delete a resume and its data |

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Database | MongoDB (Motor async driver) |
| AI | Anthropic Claude API (direct) or OpenRouter (proxy to many providers) - configurable, see below |

## LLM providers

`LLM_PROVIDER` in `backend/.env` selects which `LLMClient` implementation
`app/ai/factory.py` builds. Nothing else in the app (interview engine,
resume service, API routes) knows or cares which one is active.

| `LLM_PROVIDER` | Client | Requires |
|---|---|---|
| `auto` (default) | Anthropic if `ANTHROPIC_API_KEY` is set, else the stub | nothing |
| `stub` | Deterministic stub (no network calls) | nothing |
| `anthropic` | `AnthropicLLMClient`, direct Anthropic API | `ANTHROPIC_API_KEY` |
| `openrouter` | `OpenRouterLLMClient`, via [OpenRouter](https://openrouter.ai) | `OPENROUTER_API_KEY` |

Forcing `anthropic` or `openrouter` without the matching key fails loudly at
startup (`LLMConfigurationError`) rather than silently falling back to the
stub.

### OpenRouter

Uses the official `openai` Python SDK pointed at OpenRouter's `base_url`
(`https://openrouter.ai/api/v1`) - OpenRouter's own documented integration
approach; no custom HTTP client. Structured output is requested via
OpenRouter's `response_format: {"type": "json_schema", ...}` (built from
each Pydantic schema) as a hint to the model, but the response is always
independently `json.loads`'d and Pydantic-validated before being returned -
never trusted blindly. One retry with corrective feedback is attempted on a
malformed/invalid response; a second failure raises `LLMInvalidResponseError`.

`openai.*` SDK exceptions are caught in `openrouter_client.py` and
translated into provider-agnostic types (`app/ai/errors.py` -
`LLMAuthenticationError`, `LLMRateLimitError`, `LLMTimeoutError`,
`LLMConnectionError`, `LLMInvalidResponseError`) so nothing OpenRouter-
specific leaks past this one file. `OPENROUTER_MODEL` is fully configurable
(default `anthropic/claude-sonnet-5`) - never hardcoded elsewhere.

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
pip install -r requirements-dev.txt   # adds reportlab, used only to
                                        # generate real PDF fixtures in tests
pytest -v -m "not live"    # the full suite - never needs a real API key
pytest -v -m live          # optional: real OpenRouter calls, needs
                            # OPENROUTER_API_KEY and spends real credits
```

The test environment always forces `LLM_PROVIDER=stub` (see
`tests/conftest.py`), regardless of what `backend/.env` has configured for
local dev use - so `pytest -v` (no `-m` filter) never accidentally spends
API credits except for the explicitly-`live`-marked OpenRouter tests, which
skip themselves automatically when `OPENROUTER_API_KEY` isn't set.

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

**Resume upload** has no frontend yet - try it via the API directly:
```bash
curl -X POST http://localhost:8000/api/resumes -F "file=@/path/to/resume.pdf"
curl http://localhost:8000/api/resumes
```
Or use the interactive docs at http://localhost:8000/docs.

## Environment variables

See [`backend/.env.example`](backend/.env.example) for the full list. Never
commit a real `.env` file — it's git-ignored.

## Known limitations

- **`AnthropicLLMClient` is implemented but unverified against a live API
  key** in this environment - it's written against the current documented
  SDK API and type-checks, but no live model call has actually been made.
  Set `ANTHROPIC_API_KEY` and run a real interview to confirm before relying
  on it.
- **`OpenRouterLLMClient` is implemented and verified for transport/auth/
  error-handling, but not for a successful structured-output round trip** -
  the configured account returned `402 payment_required` (insufficient
  credits) on the configured model, and a free-tier model that was tried
  instead doesn't support structured outputs (`400`). Both failures were
  caught and translated cleanly (proving the error-handling code works),
  and a plain, non-structured completion against the free model succeeded
  (proving auth/transport/base_url all work) - but no real
  `generate_question`/`evaluate_answer`/`generate_follow_up_question`/
  `extract_candidate_profile` call has actually returned real data yet.
  **Add credits to the OpenRouter account to complete this verification.**
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
- **Resume ingestion has no frontend UI yet** - upload/list/get/delete only
  exist as API endpoints so far (verified via curl and the test suite); a
  Resume Manager screen (spec §26) is a small follow-up, not built this
  milestone.
- **Resume content isn't used in interviews yet** - `CandidateProfile` is
  extracted and stored, but nothing routes it into question generation.
  That's the natural next step (a "Resume-Based Interview" mode), not
  something this milestone's scope included.
- **PDF only** - the extractor interface is written to make DOCX a small
  addition, but DOCX isn't implemented.
- **Keyword-list technology detection is necessarily incomplete** - it
  catches common languages/frameworks/databases/tools, not everything;
  the LLM structuring pass supplements it but isn't exhaustive either.

## Roadmap

Following the milestone plan from the product spec:

1. **Foundation** — repo, frontend/backend/DB wiring, health check *(done)*
2. **Interview MVP** — setup → question → answer → evaluation → next question *(done)*
3. **Persistence** — interview history *list UI* (individual reports + all
   underlying data already exist as of Milestone 2)
4. **Resume ingestion** — upload, extraction, structured profile *(done - see Known limitations for what's still missing: frontend UI, DOCX, wiring into question generation)*
5. **Adaptive interviewing** — difficulty adaptation, follow-ups, weak-topic detection *(done - within a single session; see Known limitations)*
6. **Analytics** — progress tracking, *cross-interview* recurring weaknesses, prep plans
7. **Job/Company mode** — JD analysis, role-specific interviews
8. **Voice interviews** — STT/TTS, live interview UI
9. **Production hardening** — auth, security, logging, deployment

## License

Personal project — not currently licensed for reuse.
