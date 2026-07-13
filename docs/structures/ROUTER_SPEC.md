# Router session lifecycle (deferred)
**Status:** spec only — `routers/session.py` not implemented yet. Engine graph is
clinical intake only (starts at `presenting_complaint`, ends at `complete`).
Consent and survey live outside the graph; builders are in
`apps/api-server/engine/deterministic_forms.py`.
When the router milestone starts, drive behaviour from `Encounter.status`
**before** touching the graph:
| `Encounter.status` | Router does |
| --- | --- |
| `NOT_STARTED` | Return consent `NextStep` via `build_next_step_raw(0, build_consent_questions(), phase="consent")` — **no** `graph.invoke`. On respond: write `Consent` row(s), flip status → `IN_PROGRESS`, **then** first `graph.invoke(...)` (start, not resume) → enters `presenting_complaint`. |
| `IN_PROGRESS` | Normal `Command(resume=answer)` into the graph. |
| Graph reaches `complete` (`is_session_complete=True`) | If org has configured `Survey` and no `SurveyResponse` yet → return survey `NextStep` via `build_next_step(state, build_survey_questions() or Survey.schema, phase="survey")` — **no** graph. On respond: write `SurveyResponse` directly, then final complete. |
| No survey, or survey already answered | Return `NextStep(step_type="complete")`. |
## What stays in the graph vs router
| Concern | Owner |
| --- | --- |
| Consent form + `Consent` rows + `NOT_STARTED` → `IN_PROGRESS` | Router |
| Clinical intake nodes + LangGraph checkpoints | Engine |
| Silent nurse `encounter_summary` (`review` node) | Engine (no patient interrupt) |
| Optional post-intake survey + `SurveyResponse` | Router |
| Final `step_type=complete` to frontend | Router (after survey check) |
## Open question — do not decide silently
Does existing `EncounterStatus.AWAITING_REVIEW` get reused to mean
“graph done, survey pending”?
- Name is awkward now: `review` is silent/internal (clinician dashboard
  summary), not a patient-facing step.
- Alternatives: keep `IN_PROGRESS` until survey done then `COMPLETED`; add a
  new status; or repurpose `AWAITING_REVIEW` with a clear glossary update in
  DATABASE.md.
**Ask product/architecture before wiring status transitions in the router.**
## Related
- [USERFLOW.md](USERFLOW.md) — graph vs router diagram
- [APISTRUCTURE.md](../apps/api-server/APISTRUCTURE.md) — HTTP surface
- `engine/deterministic_forms.py` — consent/survey QuestionField builders