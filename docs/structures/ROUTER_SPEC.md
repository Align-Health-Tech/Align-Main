# Router session lifecycle (deferred)
**Status:** spec only — `routers/session.py` not implemented yet. Engine graph is
clinical intake only (starts at `presenting_complaint`, ends at `complete`).
Consent and survey live outside the graph; builders are in
`apps/api-server/engine/static/deterministic_forms.py`.
When the router milestone starts, drive behaviour from `Encounter.status`
**before** touching the graph:
| `Encounter.status` | Router does |
| --- | --- |
| `NOT_STARTED` | Return consent `NextStep` via `build_next_step_raw(0, build_consent_questions(), phase="consent")` — **no** `graph.invoke`. On respond: write `Consent` row(s), flip status → `IN_PROGRESS`, **then** first `graph.invoke(...)` (start, not resume) → enters `presenting_complaint`. |
| `IN_PROGRESS` | Normal `Command(resume=answer)` into the graph. |
| Graph reaches `complete` (`is_session_complete=True`) | If org has configured `Survey` and no `SurveyResponse` yet → return survey `NextStep` via `build_next_step(state, build_survey_questions() or Survey.schema, phase="survey")` — **no** graph. On respond: write `SurveyResponse`. Then (or if no survey): set encounter status → **`AWAITING_REVIEW`** and return patient `NextStep(step_type="complete")`. |
| `AWAITING_REVIEW` | Patient intake finished; clinician dashboard shows the encounter for review. **Not** “survey pending.” Graph `review` node (silent nurse summary) already ran inside the graph before `complete`. |
| Clinician marks complete | Dashboard action → status → **`COMPLETED`**. |
## What stays in the graph vs router
| Concern | Owner |
| --- | --- |
| Consent form + `Consent` rows + `NOT_STARTED` → `IN_PROGRESS` | Router |
| Clinical intake nodes + LangGraph checkpoints | Engine |
| Silent nurse `encounter_summary` (`review` node) | Engine (no patient interrupt) |
| Optional post-intake survey + `SurveyResponse` | Router (patient; before or as part of flipping to `AWAITING_REVIEW`) |
| `AWAITING_REVIEW` → `COMPLETED` | Clinician dashboard (“mark as complete”), not the patient graph |
| Final patient `step_type=complete` | Router (after graph done + optional survey) |
| Which graph to compile (`segment_type`) | Router → `SessionRunner(segment_type=…)` / `build_graph(segment_type)` — look up `Organization.segment_type` from the encounter’s `organization_id`. Only `URGENT_CARE` is registered today (`engine/topology/`). Physio/GP are future additive registrations. |
## Status meanings (decided)
| Status | Meaning |
| --- | --- |
| `NOT_STARTED` | Consent not yet accepted |
| `IN_PROGRESS` | Patient in clinical graph (and optional post-graph survey, if offered before the status flip) |
| `AWAITING_REVIEW` | Patient-side intake done; waiting for **clinician** to review and mark complete |
| `COMPLETED` | Clinician clicked mark-as-complete |

Do **not** overload `AWAITING_REVIEW` to mean “survey pending.” Survey is a patient router step; clinician review is what the status name means.
## Related
- [USERFLOW.md](USERFLOW.md) — graph vs router diagram
- [APISTRUCTURE.md](../apps/api-server/APISTRUCTURE.md) — HTTP surface
- `engine/static/deterministic_forms.py` — consent/survey QuestionField builders
- `engine/topology/` — per-`segment_type` graph wiring (`URGENT_CARE` only for now)
