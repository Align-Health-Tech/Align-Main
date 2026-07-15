# api-server

FastAPI + LangGraph backend for Align. Single Python process: HTTP API, intake orchestration, and Postgres access.

Companion docs: [APISTRUCTURE.md](../../docs/apps/api-server/APISTRUCTURE.md), [ENGINE_NODES.md](../../docs/apps/api-server/ENGINE_NODES.md), [DATABASE.md](../../docs/database/DATABASE.md), [RLS.md](../../docs/database/RLS.md), [local setup](../../docs/setup/LOCAL.md), [USERFLOW](../../docs/structures/USERFLOW.md), [ROUTER_SPEC](../../docs/structures/ROUTER_SPEC.md), [structure ideation](../../docs/structures/STRUCTURE.md).

---

## Structure

```
api-server/
├── main.py                 # FastAPI app entrypoint (uvicorn target)
├── package.json            # npm scripts: dev / lint (venv + uvicorn / ruff)
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic config (DB URL from .env)
├── .env.example            # Template for local DATABASE_URL + Azure OpenAI (copy to .env)
│
├── routers/                # Transport: HTTP routes (scaffold) — no business logic
├── engine/                 # LangGraph clinical intake (+ deterministic_forms for router)
│   ├── nodes/              # Graph nodes only (no consent/survey)
│   └── deterministic_forms.py  # Consent/survey QuestionFields — router-level, not nodes
├── external_systems/
│   ├── pms/                # Practice-management Protocol + adapters
│   └── clinical_ai/        # Three peer agents + helpers (see below)
├── schemas/                # Shared Pydantic contracts (API, graph state, clinical_ai I/O)
├── db/                     # SQLAlchemy setup and persistence models
│   ├── base.py
│   └── models/
└── alembic/
    └── versions/
```

### `external_systems/clinical_ai/`

```
clinical_ai/
├── agents.py           # thin run_* wrappers (+ private Devise parse types)
├── llm_client.py       # Azure chat; run_agent / run_agent_with_tools
├── prompt_loader.py    # load prompts/{category}/{phase}.md
├── registry.py         # PRIORITY/OPTIONAL target lists + REDFLAG_SUBCATEGORIES
├── tools.py            # DuckDuckGo web_search (Devise)
└── prompts/            # phase prompts — see prompts/README.md (PC + NL categoriser/clarify ported; rest stub)
```

Public entrypoints: `run_classifier`, `run_devise_and_prioritise`,
`run_question_generation`, `run_nurse_review_summary_agent`, `translate_to_english`.

### `schemas/`

| Module | Role |
| ------ | ---- |
| `clinical_ai_io.py` | Classifier / QG / `ReviewSummaryResult` / `TranslationResult` |
| `collect_targets.py` | `CollectTarget`, `CollectPhase`, `SESSION_TO_COLLECT_PHASE`, `RedFlagSubcategory` |
| `topic_candidates.py` | Devise output + `SessionState.prioritised_topics` |
| `question_fields.py` | `QuestionField`, `NextStep` (frontend envelope) |
| `session_states.py` | LangGraph `SessionState` (+ body/intake nested shapes) |
| `jsonb_fields.py` | `NarrativeField`, `CodedField` |

---

| Path | Role |
| ---- | ---- |
| `routers/` | Request/response parsing and routing; consent/survey lifecycle (see ROUTER_SPEC) |
| `engine/` | LangGraph clinical intake (START=`presenting_complaint` → END=`complete`) |
| `engine/graph.py` / `runner.py` / `topology/` / `checkpointer.py` | Compile, public API, per-segment edges, MemorySaver |
| `engine/helpers/` | Shared pure helpers (`next_step`, `apply_answers`, codecs, translate, …) |
| `engine/static/` | Lookup/reference data outside the graph (forms, body-diagram catalogue) |
| `engine/nodes/` | Per-phase clinical nodes (via `engine.helpers.agent_bridge` → `clinical_ai.run_*`) |
| `engine/helpers/agent_bridge.py` | Engine→AI boundary — **CI patches this module** (no Azure in tests) |
| `external_systems/pms/` | PMS fetch/push adapters behind `PMSProvider` |
| `external_systems/clinical_ai/` | Three peer agents + nurse review / translation helpers |

### Tests & Azure (M5 dual track)

```bash
# CI / local graph tests — no Azure credentials required
npm test
# or: source venv/bin/activate && python -m unittest discover -s tests -p 'test_*.py'
```

- **Graph tests** mock `engine.helpers.agent_bridge.run_*` (`tests/mock_clinical_ai.py`). Classifier scripts are order-based (`side_effect=[...]`); Devise/QG are phase-based (`side_effect=fn`).
- **Prompt smoke** (non-CI): after porting a prompt under `clinical_ai/prompts/`, call the matching `run_*` once against real Azure locally and check output shape/vocab. Do not put Azure keys in CI.
| `schemas/` | Shared Pydantic models — see table above |
| `db/` | ORM base, session helpers, and table models |
| `db/models/` | SQLAlchemy mapped tables aligned with `DATABASE.md` |
| `alembic/` | Migration runner env and revision history |
