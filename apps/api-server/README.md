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
├── routers/                # Transport: session + clinician mark-complete (M6)
├── services/               # Session lifecycle + in-memory store (DB wiring → M7)
├── engine/                 # LangGraph clinical intake
│   ├── agent_bridge.py     # Engine→AI boundary — CI patches this module
│   ├── nodes/              # Graph nodes
│   ├── topology/           # per-segment graphs
│   ├── session_state_mappers/  # patient + AI result → SessionState
│   ├── helpers/            # next_step, state_codecs, completed_phases
│   └── static/             # catalogues / deterministic forms
├── intelligence/           # Clinical AI agents + prompts + registry
├── external_systems/
│   └── pms/                # Practice-management Protocol + adapters
├── schemas/                # Shared Pydantic contracts (shapes only)
├── db/                     # SQLAlchemy setup and persistence models
└── alembic/
```

### `intelligence/`

```
intelligence/
├── agents.py           # thin run_* wrappers
├── llm_client.py       # Azure chat; run_agent / run_agent_with_tools
├── prompt_loader.py    # load prompts/{category}/{phase}.md
├── registry.py         # PRIORITY/OPTIONAL targets + REDFLAG_TARGETS
├── qg_phase_validators.py
├── tools.py            # DuckDuckGo web_search (Devise)
└── prompts/            # phase prompts — see prompts/README.md
```

Engine talks to AI only via `engine.agent_bridge`: `run_classifier`,
`run_devise_and_prioritise`, `run_question_generation`,
`run_nurse_review_summary_agent`, `translate_to_english`,
`build_agent_context`, `devise_then_generate`.

### `schemas/`

| Module | Role |
| ------ | ---- |
| `literals.py` | Shared `Literal` vocabularies (import from here only) |
| `clinical_ai_io.py` | Classifier / QG / `ReviewSummaryResult` / `TranslationResult` |
| `collect_targets.py` | `CollectTarget` + `SESSION_TO_COLLECT_PHASE` |
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
| `engine/session_state_mappers/` | `map_patient_answers` / `map_ai_result` + phase mappers + `narrative.py` |
| `engine/helpers/` | `next_step`, `state_codecs`, `completed_phases` |
| `engine/static/` | Lookup/reference data (forms, body-diagram catalogue) |
| `engine/agent_bridge.py` | Engine→intelligence boundary (CI patch seam) |
| `engine/nodes/` | Per-phase clinical nodes (AI only via `engine.agent_bridge`) |
| `intelligence/` | Agents, prompts, registry, QG validators |
| `external_systems/pms/` | PMS fetch/push adapters behind `PMSProvider` |
| `schemas/` | Shared Pydantic models — see table above |
| `db/` | ORM base, session helpers, and table models |
| `alembic/` | Migration runner env and revision history |

### Tests & Azure (M5 dual track)

```bash
# CI / local graph tests — no Azure credentials required
npm test
# or: source venv/bin/activate && python -m unittest discover -s tests -p 'test_*.py'
```

- **Graph tests** mock `engine.agent_bridge.run_*` (`tests/mock_clinical_ai.py`). Classifier scripts are order-based (`side_effect=[...]`); Devise/QG are phase-based (`side_effect=fn`).
- **Prompt smoke** (non-CI): after porting a prompt under `intelligence/prompts/`, call the matching `run_*` once against real Azure locally and check output shape/vocab. Do not put Azure keys in CI.
