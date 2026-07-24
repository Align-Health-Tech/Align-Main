# Structure

---

## 1. Folders (api-server) — who calls whom

```mermaid
flowchart TB
  R[routers]
  SVC[services]
  E[engine]
  F[forms]
  C[catalogues]
  INT[intelligence]
  PMS[external_systems/pms]
  DB[db]

  R --> SVC
  SVC --> E
  SVC --> F
  E --> INT
  E --> C
  E -.->|M7 / planned| PMS
  E -.->|M7 / planned| DB
  PMS -.->|M7 / planned| DB

  S[[schemas — shared contracts]]
```



Arrow = runtime call / import of that package. `schemas` is shared by all folders above (not drawn as edges).


| Folder                    | Owns                                                                                                                        | Calls                                                  |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| **routers/**              | HTTP parse/validate; map exceptions → status codes                                                                          | `services`                                             |
| **services/**             | Encounter status machine; in-memory session/org store (M6); pick `SessionRunner` by `segment_type`                          | `engine`, `forms`                                      |
| **forms/**                | Consent/survey `QuestionField` builders (not graph nodes)                                                                   | None                                                   |
| **engine/**               | LangGraph clinical intake: nodes, topology, runner, checkpointer, `agent_bridge`, session_state_mappers, next_step / codecs | `intelligence` (via `agent_bridge` only), `catalogues` |
| **catalogues/**           | Body-diagram SVG region tables (prefill / coding)                                                                           | None                                                   |
| **intelligence/**         | Agents `run_`*, prompts, registry, QG validators, LLM client                                                                | None                                                   |
| **external_systems/pms/** | PMS Protocol + adapters (plain I/O)                                                                                         | None                                                   |
| **db/**                   | SQLAlchemy models / persistence                                                                                             | None                                                   |
| **schemas/**              | Shared contracts: Literals, `SessionState`, `NextStep`, agent I/O, collect targets                                          | None                                                   |


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
  participant A as engine.agent_bridge

  E->>S: build Input / context
  E->>A: run_*(...)
  A-->>E: Result / TopicCandidate[]
  E->>S: update SessionState / NextStep
```



Replace David/Kevin Devise later by swapping `run_devise_and_prioritise` body — keep `list[TopicCandidate]`. No Protocol. Nodes talk to AI only via `engine.agent_bridge`.