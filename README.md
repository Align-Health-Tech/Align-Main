# Align-Main

This is the main repo of Alignhealthtech.

The app will consist of:

- **Frontend**: one Next.js app per clinical segment
- **Backend**: a single FastAPI service that hosts both the API layer and the LangGraph orchestration engine
- **Database**: one unified Postgres instance, shared across segments and across LangGraph's checkpointer and our own business tables

---

## 1. Tech stack


| Layer               | Choice                                                |
| ------------------- | ----------------------------------------------------- |
| Backend framework   | FastAPI (Python)                                      |
| Orchestration       | LangGraph                                             |
| ORM                 | SQLAlchemy + Alembic                                  |
| DB                  | Local Postgres now → Supabase or Azure Postgres later |
| Frontend            | Next.js, one app per segment                          |
| Type contract       | Pydantic → OpenAPI → `openapi-typescript`             |
| FHIR target version | R4 (not currently in scope)                           |
| FHIR server         | Microsoft FHIR service (not currently in scope)       |
| CI/CD               | GitHub Actions + pre-commit hooks                     |
| Deployment          | Docker containers, one per app                        |


---

## 2. Agent structure

LillyV1.jpg


| Agent                         | Job                                                | Input                                                    | Output                                                       |
| ----------------------------- | -------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------ |
| **Classifier agent**          | Binary/categorical judgment                        | Free-text patient input                                  | A classification (e.g. physical/localised vs non-localised)  |
| **Devise & Prioritise agent** | Clinical reasoning — decide *what* should be asked | Previous conversation state + tools (web search for now) | Ranked list of topics + red flag markers (not questions yet) |
| **Question Generation agent** | Conversational reasoning — decide *how* to ask it  | Topic list + conversation context                        | A batch of natural-language questions or a single question   |


### Why Devise & Prioritise is a separate agent

David/Kevin are building a clinical reasoning capability in parallel. If it sits behind a clean interface, our fallback implementation and their engine can be swapped without touching anything else.

### Graph node flow

```
patient_registration           (deterministic form)
  → presenting_complaint_agent (classifier: localised? Y/N)
      ├─ Yes → localised_detail_agent   (question_gen: body diagram, severity, duration, radiation)
      └─ No  → non_localised_agent      (question_gen: severity, duration, frequency)
  → devise_and_prioritise_agent (tools: web search → ranked topics + red flags)
  → priority_questions_agent    (question_gen, max 4, from top-ranked topics)
  → optional_questions_agent    (question_gen, max 4, user can skip)
  → ice_agent                   (question_gen: ideas/concerns/expectations)
  → review_node                 (deterministic summary)
  → optional_survey_node        (deterministic form)
```

---

### Per-segment apps

Three Next.js apps in the monorepo, one per clinical segment. Only `urgent-care-app` is being actively built for the demo; `physio-app` and `gp-app` are scaffolded (folders + shared config) but empty until their segment goes live.

```
Align-Main/
├── apps/
│   ├── physio-app/          # not build yet
│   ├── urgent-care-app/      # Next.Js frontend app
│   ├── gp-app/                 # not built yet
│   └── api-server/             # FastAPI + LangGraph, single Python process
│       ├── routers/            # session.py (patient) / clinician.py / demo.py
│       ├── engine/             # graph.py, nodes/, state.py
│       ├── external_systems/   # pms/, clinical_reasoning/ — Protocol + adapters
│       └── db/                 # SQLAlchemy models, Alembic migrations
├── packages/
│   ├── generated-types/       # openapi-typescript output — never hand-edit
│   └── ui/                     # shared frontend components
└── docker-compose.yml          # local Postgres + api-server
```

---

## 3. System diagram

High-level layout: one marketing landing page, three segment frontends (urgent care / GP / physio), one shared FastAPI backend, Postgres, external AI providers, and PMS adapters.

Align high-level system diagram

### Route structure (per app)

```
/patient/organisation_id   — Not in a current scope
/clinician/...                       — Not in a current scope
/demo/...                            — Public endpoint showing both patient demo and clinician portal
middleware
```

---

## 4. Specific Documents

- [API structure](docs/apps/api-server/APISTRUCTURE.md)
- [Database schema](docs/database/DATABASE.md)
- [Database RLS](docs/database/RLS.md)
- [Repository conventions](docs/repository-rule/REPOSITORYRULE.md)
- [Structure ideation](docs/structures/structure.md)