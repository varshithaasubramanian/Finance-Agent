# Finch — AI Personal Finance & Budget Agent

A full-stack personal budgeting and expense-tracking application with an AI
financial assistant. Define a monthly budget, split it into categories, log
expenses by hand or in plain English, and get deterministic analytics,
forecasts, alerts, and an affordability check — all backed by a calculation
engine that is the single source of truth for every number in the app. The
AI layer only ever *narrates* numbers it retrieves from that engine; it
never invents them, and everything keeps working with an AI key.

---

## 1. Project overview

- **Budgeting**: total monthly budget split into categories (Food, Travel,
  Education, Shopping, Entertainment, Bills, Health, Others, or your own).
- **Expense tracking**: manual form entry or natural-language entry
  ("Spent 60 on auto to college") with AI parsing and a regex/keyword
  fallback when no AI key is configured.
- **Analytics**: category/overall spend, remaining budget, % used, daily
  averages, safe daily spending, projected end-of-month spend, and
  surplus/deficit — all computed server-side with `Decimal` arithmetic.
- **Travel budget**: fixed (e.g. bus pass) vs variable travel spending,
  recommended daily travel budget, exhaustion date projection.
- **AI Assistant**: ask questions like "How much can I spend today?" — the
  assistant calls backend tools for real numbers and narrates the answer.
- **"Can I afford this?"**: dedicated Yes/No/Caution affordability check.
- **Alerts**: INFO/WARNING/CRITICAL spending alerts at 50/75/90/100%
  thresholds and pace-of-spend warnings.
- **Forecasting**: transparent linear-average projection, with an optional
  recency-weighted refinement once enough data exists (never a black-box
  ML model).
- **Recurring expenses & financial goals**: subscriptions/fees factored
  into forecasts and affordability; simple savings goal tracking.

## 2. Features

See the checklist above — every feature in the original spec is
implemented: budget setup, category CRUD with over-allocation protection,
expense CRUD/search/filter/sort, dual-mode expense entry (form + AI),
travel budget math, full analytics engine, AI assistant with tool/function
calling and a complete deterministic fallback, "Can I afford this?", alerts,
transparent forecasting, dashboard with charts, recurring expenses, and
financial goals.

## 3. Architecture

```
Browser (React/Vite SPA)
        │  REST (JSON) over HTTP
        ▼
FastAPI backend
  ├─ api/            HTTP routers (thin controllers)
  ├─ services/        deterministic calculation engine — SINGLE SOURCE OF TRUTH
  ├─ ai/               AI client, tool schemas, NL parser, assistant — all
  │                    with rule-based fallbacks when no API key is set
  ├─ models/           SQLAlchemy ORM models
  ├─ schemas/          Pydantic request/response contracts
  ├─ database/         engine/session + demo data seeding
  └─ utils/            Decimal-safe math, date/period helpers
        │
        ▼
   SQLite (local file, finance_agent.db)
```

**Key design decision — single source of truth:** every financial number
the AI assistant states is retrieved by calling a backend tool function
(`app/ai/tools.py`) that wraps the deterministic engine
(`app/services/analytics_service.py` etc.). The AI is instructed never to
calculate a number itself. This is enforced by the system prompt and by
the tool-calling architecture (the model can only get numbers via tools).

**Key design decision — AI is fully optional.** Every AI-touching feature
(NL expense parsing, the assistant, insight narration) has a complete,
tested, deterministic fallback. Leave `AI_API_KEY` empty and the app is 100%
functional — you'll just get rule-based parsing/answers instead of
free-form natural language.

**Real multi-user accounts.** Every person who signs up gets their own
private budgets, expenses, categories, recurring expenses, and goals —
nobody else can see or modify them. Auth is JWT-based (`app/auth/`):
`POST /api/auth/signup` and `/login` return a bearer token, which the
frontend attaches to every request; every resource route resolves the
current user from that token and scopes all queries to it
(`get_owned_budget_or_404` etc. enforce this at the service layer, not just
in the UI). Passwords are hashed with bcrypt and never stored or logged in
plain text.

A separate, isolated demo account (`demo@financeagent.local`) is
auto-seeded on startup when `SEED_DEMO_DATA=true` purely so a fresh clone
has something to look at; it has no discoverable password and is unrelated
to real signups. Set `SEED_DEMO_DATA=false` in production.

## 4. Technologies

**Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x, SQLite,
Pandas/NumPy (forecasting), Anthropic Python SDK (optional AI), pytest.

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts, React
Router, Axios, lucide-react icons.

## 5. Folder structure

```
finance-agent/
├── backend/
│   ├── app/
│   │   ├── api/            budgets, categories, expenses, analytics, ai, goals, recurring
│   │   ├── models/          models.py — User, Budget, Category, Expense,
│   │   │                    RecurringExpense, FinancialGoal, AIInsight
│   │   ├── schemas/         schemas.py — all Pydantic contracts
│   │   ├── services/        budget/category/expense/analytics/forecast/
│   │   │                    alert/affordability/goal/recurring services
│   │   ├── ai/               ai_client.py, tools.py, nlp_parser.py, assistant.py
│   │   ├── database/         db.py, seed.py
│   │   ├── utils/            decimal_utils.py, date_utils.py
│   │   └── main.py
│   ├── tests/                 33 pytest tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/       ui.tsx, Layout.tsx, CategoryIcon.tsx
│   │   ├── pages/             Dashboard, BudgetSetup, Expenses, AddExpense,
│   │   │                      Analytics, AIAssistant, Categories, Settings
│   │   ├── services/api.ts    full API client
│   │   ├── hooks/useBudget.tsx
│   │   ├── types/index.ts
│   │   └── utils/format.ts
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── .gitignore
└── README.md
```

## 6. Installation

Prerequisites: **Python 3.11+**, **Node.js 20+**, **npm**.

```bash
git clone <this-repo>
cd finance-agent
```

## 7. Environment variables

Backend (`backend/.env`, copy from `backend/.env.example`):

```
DATABASE_URL=sqlite:///./finance_agent.db
AI_API_KEY=
AI_MODEL=claude-3-5-haiku-latest
AI_PROVIDER=anthropic
SECRET_KEY=change-this-to-a-random-secret-in-production
APP_ENV=development
JWT_EXPIRE_MINUTES=10080
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SEED_DEMO_DATA=true
```

Frontend (`frontend/.env`, copy from `frontend/.env.example`):

```
VITE_API_BASE_URL=http://localhost:8000
```

Never commit real secrets — `.env` is git-ignored; only `.env.example`
files are tracked.

## 8. Database setup

No manual migration step is needed for local development: SQLite tables
are created automatically on backend startup (`init_db()` in
`app/database/db.py`, called from `main.py`'s startup event), and demo
data is seeded automatically the first time (`SEED_DEMO_DATA=true` by
default). To reset the database, stop the server and delete
`backend/finance_agent.db`, then restart.

## 9. How to run the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # edit if you want AI enabled
uvicorn app.main:app --reload
```

Backend runs at **http://localhost:8000**. Interactive Swagger docs at
**http://localhost:8000/docs** (ReDoc at `/redoc`).

## 10. How to run the frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend runs at **http://localhost:5173** and talks to the backend at the
URL in `VITE_API_BASE_URL`.

Open http://localhost:5173 — with `SEED_DEMO_DATA=true` (the default)
you'll immediately see a populated dashboard.

## 11. How to enable AI

The app works fully without AI. To enable natural-language expense entry
and free-form assistant chat:

1. Get an API key from an Anthropic-compatible provider.
2. In `backend/.env`, set:
   ```
   AI_API_KEY=sk-ant-...
   AI_MODEL=claude-3-5-haiku-latest
   ```
3. Restart the backend. The Settings page and `/api/budgets/{id}/assistant/status`
   will report `ai_enabled: true`.

Without a key, `/parse-expense` uses a regex/keyword parser and the
assistant uses pattern-matched deterministic answers — both are fully
tested and always available.

## 12. How to use demo data

Demo data seeds automatically on first run (`SEED_DEMO_DATA=true` in
`.env`): a budget of ₹2,000 for the current month (Food ₹1,000, Travel
₹800 with a ₹300 fixed bus pass, Others ₹200, plus empty Education/
Entertainment categories), a spread of realistic sample expenses, one
recurring expense, and one financial goal. Set `SEED_DEMO_DATA=false` to
start empty and use the **Budget Setup** page instead.

## 13. API documentation

Full interactive docs are auto-generated by FastAPI at `/docs` once the
backend is running. Summary of REST resources (all under `/api`):

| Resource | Endpoints |
|---|---|
| Auth | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` |
| Budgets | `GET/POST /budgets`, `GET /budgets/current`, `GET/PATCH /budgets/{id}` (all scoped to the logged-in user) |
| Categories | `GET/POST /budgets/{id}/categories`, `PATCH/DELETE /budgets/{id}/categories/{cid}` |
| Expenses | `GET/POST /budgets/{id}/expenses` (filter/search/sort via query params), `PATCH/DELETE /budgets/{id}/expenses/{eid}` |
| Analytics | `GET /budgets/{id}/summary`, `/travel`, `/trends`, `/forecast`, `/alerts` |
| Affordability | `POST /budgets/{id}/affordability` |
| NL parsing | `POST /budgets/{id}/parse-expense` |
| AI assistant | `POST /budgets/{id}/assistant/ask`, `GET /budgets/{id}/assistant/status` |
| Recurring | `GET/POST /budgets/{id}/recurring`, `DELETE .../{{rid}}`, `POST .../{{rid}}/deactivate` |
| Goals | `GET/POST /goals`, `PATCH/DELETE /goals/{gid}` |

All error responses follow `{"detail": "...", "error_code": "..."}`.

## 14. Testing

Backend (33 tests covering budget math, category remaining amounts, daily
allowance, travel fixed/variable math matching the spec's own example,
overspending, forecasting, affordability, NL parsing, and API integration
including over-allocation protection):

```bash
cd backend
source venv/bin/activate
pytest -v
```

All tests use an isolated SQLite file separate from your dev database and
reset schema between tests.

Frontend: the codebase is structured for component testing (Vitest +
React Testing Library would slot in cleanly against the existing
`components/`/`pages/` split); no test runner is pre-wired in this build to
keep the deliverable focused, but `npm run build`'s TypeScript check
(`tsc -b`) passes cleanly and is verified as part of this project.

## 15. Future improvements

- Bank/UPI statement import (CSV) for bulk expense entry
- Push/email notifications for CRITICAL alerts
- Password reset / email verification flow
- Multi-currency support (the schema already carries `currency`/`currency_symbol`)
- Streaming AI assistant responses
- Automated frontend test suite (Vitest + React Testing Library)

---

## Docker (optional)

```bash
docker compose up --build
```

This builds and runs both services: backend on `:8000`, frontend on
`:5173`. Set `AI_API_KEY` in your shell environment before running to
enable AI features in the containerized build. By default this still uses
a local SQLite file inside the backend container; see "Deploying to the
web" below for a persistent Postgres setup.

---

## 16. Deploying to the web

The app is two independently deployable pieces: a FastAPI backend and a
static-built React frontend. A free-tier-friendly path is **Render**
(backend + database) and **Vercel** (frontend).

### Step 1 — push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<you>/finance-agent.git
git branch -M main
git push -u origin main
```

`.gitignore` already excludes `venv/`, `node_modules/`, `.env`, and `*.db`.

### Step 2 — a persistent database (Postgres)

SQLite is a single file; most hosting platforms wipe the filesystem on
every redeploy/restart, so **for data to survive, use Postgres in
production.** The app already reads `DATABASE_URL` generically and
`psycopg2-binary` is already in `requirements.txt`, so this is just a
connection-string change:

1. On Render: **New → PostgreSQL** (free tier available). Copy the
   "Internal Database URL" it gives you.
2. You'll paste that into the backend's `DATABASE_URL` environment
   variable in Step 3 below. It will look like
   `postgresql://user:pass@host/dbname` (if a host ever gives you
   `postgres://` instead, the app normalizes that automatically).

### Step 3 — deploy the backend (Render)

1. https://render.com → sign up → connect GitHub
2. **New → Web Service** → select your repo
3. Configure:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Environment variables:
   - `DATABASE_URL` = the Postgres URL from Step 2 (omit this to keep using
     ephemeral SQLite for a quick demo instead)
   - `SECRET_KEY` = a long random string (`python -c "import secrets; print(secrets.token_hex(32))"`)
     — this signs login sessions; treat it like a password
   - `SEED_DEMO_DATA` = `false` (you don't want the demo account seeded
     into your production database)
   - `CORS_ORIGINS` = leave for now, fill in after Step 4
   - `AI_API_KEY` = optional
5. **Create Web Service**. You'll get a URL like `https://finance-agent-backend.onrender.com`.

### Step 4 — deploy the frontend (Vercel)

1. https://vercel.com → sign up → connect GitHub
2. **Add New → Project** → select your repo
3. Configure:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Environment variable:
   - `VITE_API_BASE_URL` = your Render backend URL from Step 3
5. **Deploy**. You'll get a URL like `https://finance-agent.vercel.app`.

### Step 5 — connect them

Back on Render → your backend service → Environment → set:
```
CORS_ORIGINS=https://finance-agent.vercel.app
```
Save (triggers a redeploy).

### Step 6 — test it

Visit your Vercel URL, sign up for an account, create a budget, add an
expense, then close the tab and reopen it — you should stay logged in
(the token is stored in the browser) and your data should be exactly as
you left it. Open the site in an incognito window and sign up with a
different email to confirm the second account starts empty and can't see
the first account's data.

**Anyone with the Vercel URL can now sign up and use the app with their
own private data** — that's what the JWT auth layer added in this build
enables.


---

## Quick start (TL;DR)

```bash
# Terminal 1
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && cp .env.example .env
uvicorn app.main:app --reload

# Terminal 2
cd frontend && npm install && cp .env.example .env
npm run dev
```

Visit **http://localhost:5173**.
