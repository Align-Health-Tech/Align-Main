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
│   └── …
├── forms/                  # Router-level consent/survey QuestionField builders
├── catalogues/
│   └── body_diagram/       # SVG region catalogue (engine LOCALISED)
├── urls/                   # Reviewed Healthify / Health NZ evidence catalogues
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
├── llm_client.py       # Azure Responses API; run_agent / run_agent_with_tools
├── prompt_loader.py    # load prompts/{category}/{phase}.md
├── registry.py         # PRIORITY/OPTIONAL targets + REDFLAG_TARGETS
├── qg_phase_validators.py
├── tools.py            # Curated catalogue ranking + bounded parallel HTML fetch
└── prompts/            # phase prompts — see prompts/README.md
```

Engine talks to AI only via `engine.agent_bridge`: `run_classifier`,
`run_devise_and_prioritise`, `run_question_generation`,
`run_nurse_review_summary_agent`, `translate_to_english`,
`build_agent_context`, `devise_then_generate`.

### Azure model runtime

`intelligence/llm_client.py` intentionally constructs
`AzureChatOpenAI(..., use_responses_api=True)` for the GPT-5.4 deployment. It
uses `reasoning_effort="low"`, a 60-second request timeout, and no SDK retries.
Do not replace this with `ChatOpenAI(base_url=...)` without rerunning the real
Azure classifier, priority, and red-flag smokes.

Runtime and `--real-azure` scripts require:

| Variable | Contract |
| -------- | -------- |
| `AZURE_OPENAI_API_KEY` | Key for the Azure resource |
| `AZURE_OPENAI_ENDPOINT` | Exact resource endpoint, for example `https://<resource>.cognitiveservices.azure.com/` |
| `AZURE_MODEL_NAME` | Azure **deployment name**, which may differ from the base model ID |
| `AZURE_OPENAI_API_VERSION` | Optional; defaults to `2025-04-01-preview` |

GPT-5.4 Responses does not accept a configurable `temperature` in this
integration. See [local setup](../../docs/setup/LOCAL.md#4-azure-openai-responses-api).

### Curated clinical evidence

The public LangChain tool name remains `web_search`, but it never performs
general web search. It reads the two repository CSVs in explicit order:
Healthify first, then Health NZ. The BOM-compatible loader requires `title`
and `url`, ignores extra export columns, and caches parsed catalogues. It
rejects malformed, non-HTTPS, placeholder, credential-bearing, port-bearing,
fragmented, or non-allowlisted URLs. The exact permitted hosts are
`healthify.nz` and `www.healthnz.govt.nz`.

Ranking is deterministic BM25 over normalized title and URL-slug tokens, with
an exact multi-token phrase boost. Only positive-scoring rows are returned.
Equal scores use combined catalogue row order as the final tie-break; there is
no domain preference. Selection is the top three with no padding, so a valid
query may produce zero, one, or two results.

The synchronous tool fetches selected pages concurrently with a three-worker
thread pool. Each source has a hard eight-second total deadline including
redirects, a one-megabyte body limit, at most two same-host HTTPS redirects,
and an HTML-only content policy. BeautifulSoup prefers `main`, then `article`,
then `body`; scripts, styles, navigation, headers, footers, asides, forms,
`noscript`, and SVG are removed. Readable text is capped at 12,000 characters
per source.

The structured result contains the query, successful and failed sources, BM25
scores, safe failure codes, per-source latency, and total parallel batch
latency. Output is restored to BM25 rank order, never completion order. A
partial result remains usable; zero successful fetches causes controlled
base-reasoning fallback.

Priority and red-flag Devise each have exactly one forced tool round. After the
final structured model response, candidate evidence URLs are deduplicated in
BM25 order, filtered against successfully fetched URLs, and capped at three.
Invented, mismatched, and failed URLs are removed. A candidate with at least
one validated URL keeps `source="web_search"`; otherwise it is forced to
`source="base_reasoning"` with `evidence_urls=[]`. Question Generation receives
candidate metadata and these URLs, but never fetched page text and never
refetches. Optional and clarification phases are reasoning-only.

Catalogue maintenance rules are in [`urls/README.md`](urls/README.md).

### `schemas/`

| Module | Role |
| ------ | ---- |
| `literals.py` | Shared `Literal` vocabularies (import from here only) |
| `clinical_ai_io.py` | Classifier / QG / `ReviewSummaryResult` / `TranslationResult` |
| `collect_targets.py` | `CollectTarget` + `SESSION_TO_COLLECT_PHASE` |
| `topic_candidates.py` | Devise output + `SessionState.prioritised_topics`, including validated evidence provenance (`source`, `evidence_urls`) |
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
| `forms/` | Router-level consent/survey QuestionField builders |
| `catalogues/body_diagram/` | SVG body-diagram region catalogue (engine LOCALISED) |
| `urls/` | Reviewed Healthify / Health NZ evidence URL catalogue used by Devise |
| `engine/agent_bridge.py` | Engine→intelligence boundary (CI patch seam) |
| `engine/nodes/` | Per-phase clinical nodes (AI only via `engine.agent_bridge`) |
| `intelligence/` | Agents, prompts, registry, QG validators |
| `external_systems/pms/` | PMS fetch/push adapters behind `PMSProvider` |
| `schemas/` | Shared Pydantic models — see table above |
| `db/` | ORM base, session helpers, and table models |
| `alembic/` | Migration runner env and revision history |
