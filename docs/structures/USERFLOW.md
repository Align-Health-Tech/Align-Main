```mermaid
flowchart TD
    R0[Router: consent<br/>Encounter.status=NOT_STARTED<br/>no graph]
    A2[2. presenting_complaint<br/>run_classifier — GRAPH START]
    A3a[3a. localised_detail<br/>deterministic UI]
    A3b[3b. non_localised_detail<br/>run_classifier non_localised_categoriser]
    A4[4. priority_questions]
    A5[5. redflag_screening]
    A6[6. optional_questions<br/>skippable]
    A7[7. ice]
    A8[8. review<br/>INTERNAL — dashboard summary<br/>no patient interrupt]
    A10[10. complete — GRAPH END]
    R9[Router: survey optional<br/>after is_session_complete<br/>no graph]

    R0 -->|status → IN_PROGRESS<br/>first graph.invoke| A2

    A2 -->|ready=False| B1[clarify Devise+QG → answer]
    B1 -.->|re-enter| A2
    A2 -->|ready=True LOCALISED<br/>chief_complaint ← ai_summary| A3a
    A2 -->|ready=True NOT_LOCALISED<br/>chief_complaint ← ai_summary| A3b

    A3b -->|ready=False| B2[clarify → re-enter]
    B2 -.-> A3b
    A3b -->|ready=True| B3[timing / severity / functional]
    B3 --> A4
    A3a --> A4

    A4 --> A5 --> A6 --> A7 --> A8
    A8 -->|writes encounter_summary| A10
    A10 -.->|router may offer survey| R9
```

**Graph nodes (9):** `presenting_complaint` · `localised_detail` · `non_localised_detail` · `priority_questions` · `redflag_screening` · `optional_questions` · `ice` · `review` · `complete`

**Router-level (not graph):** consent (before first invoke), survey (after graph complete). Helpers: `forms/`. Spec: [`ROUTER_SPEC.md`](ROUTER_SPEC.md).

**Patient-facing sequence frontend sees:**

1. consent (router) → 2. presenting_complaint (+ clarify) → 3a/3b → 4. priority → 5. redflag → 6. optional → 7. ice → *(silent review)* → 9. survey? (router) → complete

**`presenting_complaint` / `chief_complaint`:** Stage 1 stores the patient's free-text answer (`source: "free_text"`). On classifier `ready: true`, `map_classifier_result` overwrites `chief_complaint` with `chiefComplaintSummary` (`source: "ai_summary"`). Original patient wording stays recoverable in session `messages` (no separate DB column).

**Detail timing (3a/3b):** After routing, QG emits one adaptive `single_choice` duration question with 3–5 context-grounded chips plus `Other`. A chip answer writes `duration` with `source: "option"`; `Other` free text writes `source: "free_text"`. NL also asks deterministic severity + functional-impact scores; localised asks deterministic severity after the body diagram. NL categoriser clarify is capped at **3 rounds in code** (`non_localised_clarify_rounds` + lean force-commit) — see [ENGINE_NODES.md](../apps/api-server/ENGINE_NODES.md).

**Not patient-facing:** step 8 `review` — clinician `encounter_summary` only.
