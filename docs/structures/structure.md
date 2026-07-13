# Structure ideation

Scratchpad — not source of truth. Prefer `apps/api-server/README.md` for the live layout.

---

## 1. Layers

```mermaid
flowchart TB
  FE[Frontend]
  R[routers — HTTP]
  E[engine — LangGraph nodes]
  S[schemas — shared contracts]
  CAI[clinical_ai — run_*]
  PMS[pms — Protocol + adapters]
  DB[(Postgres)]

  FE --> R --> E
  R --> DF[deterministic_forms — consent/survey]
  E --> S
  CAI --> S
  R --> S
  E --> CAI
  E --> PMS
  E --> DB
  PMS --> DB
```

| Layer | Owns | Does not own |
| ----- | ---- | ------------ |
| **schemas** | Shapes everyone shares (`SessionState`, `NextStep`, agent I/O, `CollectTarget`, …) | LLM calls, DB writes, routing |
| **engine** | Clinical graph progress; map answers → state / graph NextSteps | Prompt text, Azure, PMS, consent/survey HTTP lifecycle |
| **deterministic_forms** (in engine/) | Consent/survey QuestionField builders for router | Graph topology |
| **clinical_ai** (runtime) | `run_*`, prompts, registry lists, tools | Graph topology, HTTP |
| **pms** (runtime) | Fetch/push behind `PMSProvider` | Clinical reasoning |

---

## 2. PMS — adapter

```mermaid
flowchart LR
  E[engine] --> P[PMSProvider Protocol]
  P --> N[NoPMSAdapter]
  P --> M[MedTechAdapter]
```

Plain I/O, no LLM. Swap adapter via org `pms_config.vendor` — engine stays the same.

---

## 3. Clinical AI — agents

Three peers + helpers. Red flag = Devise + QG with `phase=redflag_screening`, not a 4th agent.

```mermaid
flowchart TB
  subgraph peers [Three peers]
    C[run_classifier]
    D[run_devise_and_prioritise]
    Q[run_question_generation]
  end
  subgraph helpers [Helpers]
    N[run_nurse_review_summary_agent]
    T[translate_to_english]
  end

  D -->|web_search tool| W[DuckDuckGo]
  C --> L[llm_client + prompts/]
  D --> L
  Q --> L
  N --> L
  T --> L
```

```mermaid
sequenceDiagram
  participant E as engine node
  participant S as schemas
  participant A as clinical_ai

  E->>S: build Input / context
  E->>A: run_*(...)
  A-->>E: Result / TopicCandidate[]
  E->>S: update SessionState / NextStep
```

Replace David/Kevin Devise later by swapping `run_devise_and_prioritise` body — keep `list[TopicCandidate]`. No Protocol.
