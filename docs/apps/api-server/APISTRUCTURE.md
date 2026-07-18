# apps/api-server — API reference

FastAPI + LangGraph, single process. Target endpoint surface — what each route will touch in the DB once implemented.

Companion docs: [DATABASE.md](../../database/DATABASE.md) (schema), [RLS.md](../../database/RLS.md) (access rules per table), [ROUTER_SPEC.md](../../structures/ROUTER_SPEC.md) (consent/survey outside graph), [USERFLOW.md](../../structures/USERFLOW.md).

**M6 note:** Patient + clinician mark-complete routes are wired against an
**in-memory** store (`services/`). Responses include `status` for lifecycle
verification. Real Patient/Encounter/Consent/SurveyResponse SQL + auth/RLS
land in M7. Tables-touched rows below describe the target persistence model.

---

## 1. Patient session lifecycle (`routers/session.py`) - Preconsultation

The whole intake flow — however many phases or nodes it has internally — collapses to three calls. This is deliberate: the frontend never needs a new endpoint when a node is added, removed, or reordered.

Currently we only have guest workflow and therefore using endpoint, we only create `patient.kind = GUEST` .

### `POST /sessions`

Called once, on QR scan or a URL open.


|                |                                                                                                                                                           |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Auth           | QR or URL only                                                                                                                                            |
| Role           | `align_app`, `is_patient() = true` after this call sets `current_encounter_id`                                                                            |
| Request        | None                                                                                                                                                      |
| Response       | `{ session_id: str, next_step: NextStep, status: EncounterStatus }` (M6 adds `status`)                                                                    |
| Tables touched | Creates `Patient` (`kind = GUEST`) and `Encounter` (`status = NOT_STARTED`). `Encounter.id` becomes `session_id` and doubles as the LangGraph `thread_id` |


### `POST /sessions/{id}/respond`

The loop. Called once per patient answer, however many times that ends up being.


|                |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Auth           | Session-scoped — `id` must match the caller's `current_encounter_id`                                                                                                                                                                                                                                                                                                                                                                                                                |
| Role           | `align_app`, `is_patient() = true`                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Request        | `{ answer: ... }` — shape depends on the current `step_type`                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Response       | `{ next_step: NextStep, status: EncounterStatus }`                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Tables touched | Varies by step — `Consent` (router, gates `Encounter.status → IN_PROGRESS` before first graph invoke), graph-driven `Encounter` columns / `BodyStructure` / `Flag` / `IntakeFactItem`, router-driven `SurveyResponse` after graph complete, plus `LillyAiInteraction`/`AuditLog` as engine-internal writes (via `align_engine`, not this request's `align_app` context — see [RLS.md](../../database/RLS.md)). Lifecycle detail: [ROUTER_SPEC.md](../../structures/ROUTER_SPEC.md). |


### `GET /sessions/{id}`

Read-only. Covers both "resume after a refresh" and "review a completed session" — no separate `/summary` endpoint.


|                |                                                                                     |
| -------------- | ----------------------------------------------------------------------------------- |
| Auth           | Session-scoped, same as above                                                       |
| Role           | `align_app`, `is_patient() = true`                                                  |
| Request        | None                                                                                |
| Response       | `{ next_step: NextStep, status: EncounterStatus }`                                  |
| Tables touched | None written — reads current `Encounter` state via the checkpointer/business tables |


---

## 2. Clinician dashboard (`routers/clinician.py`)

### `GET /clinician/sessions?status=active`


|                |                                                           |
| -------------- | --------------------------------------------------------- |
| Auth           | Practitioner login (Medtech or Entra, To be decided)      |
| Role           | `align_app`, `is_patient() = false`                       |
| Response       | List of `Encounter` rows, org-scoped automatically by RLS |
| Tables touched | `Encounter` (read only)                                   |


### `GET /clinician/sessions/{id}`


|                |                                                                                                                |
| -------------- | -------------------------------------------------------------------------------------------------------------- |
| Auth           | Practitioner login (Medtech or Entra, To be decided)                                                           |
| Role           | `align_app`, `is_patient() = false`                                                                            |
| Response       | Full encounter detail                                                                                          |
| Tables touched | `Encounter`, `BodyStructure`, `RadiationSite`, `Flag`, `IntakeFactItem`, `PractitionerComment` — all read only |


### `POST /clinician/sessions/{id}/complete`

Dashboard “mark as complete” — flips `Encounter.status` from `AWAITING_REVIEW`
→ `COMPLETED`. Not graph-driven. See [ROUTER_SPEC.md](../../structures/ROUTER_SPEC.md).


|                |                                                                            |
| -------------- | -------------------------------------------------------------------------- |
| Auth           | Practitioner login (Medtech or Entra, To be decided)                       |
| Role           | `align_app`, `is_patient() = false`                                        |
| Request        | None (or empty body)                                                       |
| Response       | `{ session_id: str, status: "COMPLETED" }`                                 |
| Preconditions  | Current status must be `AWAITING_REVIEW` — otherwise `409` (or equivalent) |
| Tables touched | `Encounter` (update `status`)                                              |


### `POST /clinician/sessions/{id}/comments`

Clinician free-text note — also not graph-driven (alongside mark-complete above).


|                |                                                      |
| -------------- | ---------------------------------------------------- |
| Auth           | Practitioner login (Medtech or Entra, To be decided) |
| Role           | `align_app`, `is_patient() = false`                  |
| Request        | `{ body: str }`                                      |
| Tables touched | `PractitionerComment` (insert)                       |


### `PUT /clinician/sessions/{id}/comments/{comment_id}` / `DELETE .../{comment_id}`

Edit or remove a comment. Restricted to the comment's own author (`practitioner_id` must match the caller).


|                |                                                  |
| -------------- | ------------------------------------------------ |
| Auth           | Practitioner login, must be the comment's author |
| Role           | `align_app`, `is_patient() = false`              |
| Request (PUT)  | `{ body: str }`                                  |
| Tables touched | `PractitionerComment` (update/delete)            |


Note: the comments that are synced to the medtech are not updatable

---

## 3. Management API (`routers/organizations.py`, `routers/practitioners.py`, `routers/admin.py`)

### Organizations — `align_admin` only


| Method   | Path                        | Request                                     | Tables touched                   |
| -------- | --------------------------- | ------------------------------------------- | -------------------------------- |
| `GET`    | `/admin/organizations`      | —                                           | `Organization` (list, cross-org) |
| `GET`    | `/admin/organizations/{id}` | —                                           | `Organization` (read)            |
| `POST`   | `/admin/organizations`      | `{ name, slug, segment_type, pms_config? }` | `Organization` (insert)          |
| `PUT`    | `/admin/organizations/{id}` | `{ pms_config?, pms_integration_config? }`  | `Organization` (update)          |
| `DELETE` | `/admin/organizations/{id}` | —                                           | `Organization` (delete)          |


### Practitioners — `align_app` (own org) + `align_admin` (cross-org)


| Method   | Path                  | Request               | Tables touched                           |
| -------- | --------------------- | --------------------- | ---------------------------------------- |
| `GET`    | `/practitioners`      | —                     | `Practitioner` (list, org-scoped by RLS) |
| `GET`    | `/practitioners/{id}` | —                     | `Practitioner` (read)                    |
| `POST`   | `/practitioners`      | `{ role, hpi_cpn? }`  | `Practitioner` (insert, org-scoped)      |
| `PUT`    | `/practitioners/{id}` | `{ role?, hpi_cpn? }` | `Practitioner` (update)                  |
| `DELETE` | `/practitioners/{id}` | —                     | `Practitioner` (delete)                  |


### Patients — `align_app` practitioner, own org


| Method   | Path             | Request                 | Tables touched                      |
| -------- | ---------------- | ----------------------- | ----------------------------------- |
| `GET`    | `/patients`      | query params for search | `Patient` (list, org-scoped by RLS) |
| `GET`    | `/patients/{id}` | —                       | `Patient` (read)                    |
| `PUT`    | `/patients/{id}` | any patient column      | `Patient` (update)                  |
| `DELETE` | `/patients/{id}` | —                       | `Patient` (delete)                  |


### Surveys — `align_admin` only


| Method | Path                  | Request                                                                                     | Tables touched             |
| ------ | --------------------- | ------------------------------------------------------------------------------------------- | -------------------------- |
| `GET`  | `/admin/surveys`      | —                                                                                           | `Survey` (list, cross-org) |
| `GET`  | `/admin/surveys/{id}` | —                                                                                           | `Survey` (read)            |
| `POST` | `/admin/surveys`      | `{ organization_id, key, schema }` — `version` auto-increments per `(organization_id, key)` | `Survey` (insert)          |
| `PUT`  | `/admin/surveys/{id}` | `{ schema? }`                                                                               | `Survey` (update)          |


### Read-only admin views — `align_admin` only


| Method | Path                      | Tables touched                         |
| ------ | ------------------------- | -------------------------------------- |
| `GET`  | `/admin/survey-responses` | `SurveyResponse` (read, cross-org)     |
| `GET`  | `/admin/audit-logs`       | `AuditLog` (read, cross-org)           |
| `GET`  | `/admin/ai-interactions`  | `LillyAiInteraction` (read, cross-org) |


---

## 4. Demo (`routers/demo.py`)

Same shape as /sessions but with /demo/sessions. The patient will be created with `patient.kind = DEMO` .

---

## 5. What's explicitly out of scope right now

- **Going back to a previous answer** — designed (LangGraph `get_state_history`/fork + business-table cleanup rules), deliberately not built for the 2-week demo. Revisit if pilot feedback asks for it.
- **Direct endpoints for `Consent`, `IntakeFactItem`, `BodyStructure`, `RadiationSite`, etc.** — not missing, just handled inside the session loop as engine side-effects rather than separate REST resources.

