# api-server

FastAPI + LangGraph backend for Align. Single Python process: HTTP API, intake orchestration, and Postgres access.

Companion docs: [APISTRUCTURE.md](../../docs/apps/api-server/APISTRUCTURE.md), [DATABASE.md](../../docs/database/DATABASE.md), [RLS.md](../../docs/database/RLS.md), [local setup](../../docs/setup/LOCAL.md).

---

## Structure

```
api-server/
├── main.py                 # FastAPI app entrypoint (uvicorn target)
├── package.json            # npm scripts: dev / lint (venv + uvicorn / ruff)
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic config (DB URL from .env)
├── .env.example            # Template for local DATABASE_URL (copy to .env)
│
├── routers/                # Transport: HTTP routes only (session / clinician / demo) — no business logic
├── engine/                 # Intelligence: LangGraph graph, state, and orchestration
│   └── nodes/              # Individual graph node implementations
├── external_systems/       # Integration adapters behind Protocol interfaces
│   ├── pms/                # Practice-management system adapters (MedTech, no-op, …)
│   └── clinical_reasoning/ # Devise & Prioritise providers (fallback LLM vs clinical engine)
├── schemas/                # Shared Pydantic shapes (API envelopes + jsonb field types)
├── db/                     # Foundation: SQLAlchemy setup and persistence models
│   ├── base.py             # Declarative Base + UUID / timestamp mixins
│   └── models/             # One module per domain table group (org, patient, encounter, …)
└── alembic/                # Schema migrations
    └── versions/           # Ordered revision scripts (initial schema, RLS, column adds, …)
```

| Path | Role |
| ---- | ---- |
| `routers/` | Request/response parsing and routing; calls into engine / services |
| `engine/` | LangGraph workflow that drives pre-consult intake |
| `engine/nodes/` | Per-phase node logic (classifier, question gen, ICE, …) |
| `external_systems/` | Swappable integrations; engine depends on Protocols, not vendors |
| `external_systems/pms/` | PMS fetch/push adapters |
| `external_systems/clinical_reasoning/` | Topic-ranking / clinical-reasoning providers |
| `schemas/` | Reusable Pydantic models (`NarrativeField`, `NextStep`, …) |
| `db/` | ORM base, session helpers, and table models |
| `db/models/` | SQLAlchemy mapped tables aligned with `DATABASE.md` |
| `alembic/` | Migration runner env and revision history |
