# Router session lifecycle

**Status:** M6 implemented — in-memory store (`services/session_store.py` +
`services/session_lifecycle.py`). HTTP: `routers/session.py`,
`routers/clinician.py`. **DB persistence of Encounter / Consent /
SurveyResponse, Postgres checkpointer, auth/RLS → M7.**

Drive behaviour from `Encounter.status` **before** touching the graph:


| `Encounter.status`                                    | Router does                                                                                                                                                                                                                                                                                                                                           |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `NOT_STARTED`                                         | Return consent `NextStep` via `build_next_step_raw(0, build_consent_questions(), phase="consent")` — **no** `graph.invoke`. On respond: stub `Consent`, flip status → `IN_PROGRESS`, **then** first `graph.invoke(...)` (start, not resume) → enters `presenting_complaint`.                                                                          |
| `IN_PROGRESS`                                         | Normal `Command(resume=answer)` into the graph.                                                                                                                                                                                                                                                                                                       |
| Graph reaches `complete` (`is_session_complete=True`) | If org has survey enabled and no survey response yet → return survey `NextStep` via `build_next_step(state, build_survey_questions(), phase="survey")` — **no** graph. Status stays `IN_PROGRESS`. On respond: stub `SurveyResponse`. Then (or if no survey): set status → `**AWAITING_REVIEW`** and return patient `NextStep(step_type="complete")`. |
| `AWAITING_REVIEW`                                     | Patient intake finished; clinician dashboard shows the encounter for review. Graph `review` node (silent nurse summary) already ran inside the graph before `complete`.                                                                                                                                                                               |
| Clinician marks complete                              | `POST /clinician/sessions/{id}/complete` → status → `**COMPLETED`**.                                                                                                                                                                                                                                                                                  |


## What stays in the graph vs router


| Concern                                                       | Owner                                                                                                                                                             |
| ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Consent form + `Consent` rows + `NOT_STARTED` → `IN_PROGRESS` | Router                                                                                                                                                            |
| Clinical intake nodes + LangGraph checkpoints                 | Engine                                                                                                                                                            |
| Silent nurse `encounter_summary` (`review` node)              | Engine (no patient interrupt)                                                                                                                                     |
| Optional post-intake survey + `SurveyResponse`                | Router (patient; before or as part of flipping to `AWAITING_REVIEW`)                                                                                              |
| `AWAITING_REVIEW` → `COMPLETED`                               | Clinician dashboard (“mark as complete”), not the patient graph                                                                                                   |
| Final patient `step_type=complete`                            | Router (after graph done + optional survey)                                                                                                                       |
| Which graph to compile (`segment_type`)                       | Router → `SessionRunner(segment_type=…)` / `build_graph(segment_type)` — look up org `segment_type`. Only `URGENT_CARE` is registered today (`engine/topology/`). |


Rationale for this design: Make it so that we can share nodes and rearrange the graphs per different clinic segements

## Status meanings (decided)


| Status            | Meaning                                                                                       |
| ----------------- | --------------------------------------------------------------------------------------------- |
| `NOT_STARTED`     | Consent not yet accepted                                                                      |
| `IN_PROGRESS`     | Patient in clinical graph (and optional post-graph survey, if offered before the status flip) |
| `AWAITING_REVIEW` | Patient-side intake done; waiting for **clinician** to review and mark complete               |
| `COMPLETED`       | Clinician clicked mark-as-complete                                                            |


## M6 stubs (pending M7)

- In-memory org + session dict (seeded default `URGENT_CARE` org)
- Consent / SurveyResponse recorded as stub dicts, not SQL rows
- MemorySaver checkpointer (not Postgres)
- No QR/auth / RLS GUCs
- Survey from `build_survey_questions()` only (not org `Survey.schema`)
- Clinician surface: mark-complete only (no list/detail/comments)

## Manual / test tools

- E2E: `tests/test_m6_session_lifecycle.py` (mocked clinical_ai + transcript)
- Interactive: `scripts/cli_session.py` (mocked by default; `--real-azure` optional)

## Related

- [USERFLOW.md](USERFLOW.md) — graph vs router diagram
- [APISTRUCTURE.md](../apps/api-server/APISTRUCTURE.md) — HTTP surface
- `forms/` — consent/survey QuestionField builders
- `engine/topology/` — per-`segment_type` graph wiring (`URGENT_CARE` only for now)

