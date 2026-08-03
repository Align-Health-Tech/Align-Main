# apps/api-server — API reference

FastAPI + LangGraph, single process.

Companion docs: [DATABASE.md](../../database/DATABASE.md) (schema), [RLS.md](../../database/RLS.md) (access rules per table), [ROUTER_SPEC.md](../../structures/ROUTER_SPEC.md) (consent/survey outside graph), [USERFLOW.md](../../structures/USERFLOW.md).

**What is actually built** — four routes:

| | |
| --- | --- |
| `POST /sessions` | create a guest session |
| `POST /sessions/{id}/respond` | the intake loop |
| `GET /sessions/{id}` | resume / review |
| `POST /clinician/sessions/{id}/complete` | `AWAITING_REVIEW` → `COMPLETED` |

They run against an **in-memory** store (`services/`), not Postgres — sessions
do not survive a restart.

Every other heading on this page is marked ***not implemented***. Those are
design work: the clinician list/detail/comments surface, the management API and
the demo router. Their schema and RLS policies do exist (`db/models/`,
`alembic/versions/`), but nothing writes to the database — `db/models` is
imported only by `alembic/env.py`. The "tables touched" rows throughout
describe that intended persistence model, not current behaviour.

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
| Response       | `{ session_id: str, next_step: NextStep, status: EncounterStatus, mirror: ClinicianMirror }` — `mirror` is empty here, the graph has not started yet      |
| Tables touched | Creates `Patient` (`kind = GUEST`) and `Encounter` (`status = NOT_STARTED`). `Encounter.id` becomes `session_id` and doubles as the LangGraph `thread_id` |


### `POST /sessions/{id}/respond`

The loop. Called once per patient answer, however many times that ends up being.


|                |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Auth           | Session-scoped — `id` must match the caller's `current_encounter_id`                                                                                                                                                                                                                                                                                                                                                                                                                |
| Role           | `align_app`, `is_patient() = true`                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Request        | `{ answer: ... }` — shape depends on the current `step_type`                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Response       | `{ next_step: NextStep, status: EncounterStatus, mirror: ClinicianMirror }`                                                                                                                                                                                                                                                                                                                                                                                                          |
| Tables touched | Varies by step — `Consent` (router, gates `Encounter.status → IN_PROGRESS` before first graph invoke), graph-driven `Encounter` columns / `BodyStructure` / `Flag` / `IntakeFactItem`, router-driven `SurveyResponse` after graph complete, plus `LillyAiInteraction`/`AuditLog` as engine-internal writes (via `align_engine`, not this request's `align_app` context — see [RLS.md](../../database/RLS.md)). Lifecycle detail: [ROUTER_SPEC.md](../../structures/ROUTER_SPEC.md). |

Operationally, the first entry into `priority_questions` and
`redflag_screening` can include a curated evidence batch. Up to three selected
sources are fetched concurrently, each with an eight-second total deadline, so
fetch time is bounded by the slowest selected source rather than the sum of
three deadlines. End-to-end response time also includes the Azure Devise
requests and QG request. Optional and clarification phases perform no evidence
fetch.


### `GET /sessions/{id}`

Read-only. Covers both "resume after a refresh" and "review a completed session" — no separate `/summary` endpoint.


|                |                                                                                     |
| -------------- | ----------------------------------------------------------------------------------- |
| Auth           | Session-scoped, same as above                                                       |
| Role           | `align_app`, `is_patient() = true`                                                  |
| Request        | None                                                                                |
| Response       | `{ next_step: NextStep, status: EncounterStatus, mirror: ClinicianMirror }`          |
| Tables touched | None written — reads current `Encounter` state via the checkpointer/business tables |


### The `mirror` field

All three session responses carry a `ClinicianMirror`
(`schemas/clinician_mirror.py`) — a read model projected from `SessionState`:

```
{ session_language, encounter_summary, fields: [{ collect_target_id, text, en_text, source }] }
```

It exists because `NextStep` only carries questions *out* to the patient and
never carries answers back. Without it the frontend could only mirror what it
had itself submitted, which meant free text stayed in the patient's language —
and the clinician dashboard is English-only.

- `text` is the patient's own wording; `en_text` is the English companion.
- `en_text` is `None` for English sessions (`text` is already English), and for
  option picks whose question generation failed to emit an `en_label`. Callers
  must render that gap rather than pass `text` off as English.
- `collect_target_id` is the join key, not the answer text: once the classifier
  is ready it overwrites `chief_complaint` with an English summary, so the
  patient's original sentence is no longer in the mirror to match against.

Rides along on the patient responses rather than getting its own authenticated
endpoint because both panes are one browser session in this build. A real
deployment would serve it from the clinician surface instead.

---

## 2. Clinician dashboard (`routers/clinician.py`)

### `GET /clinician/sessions?status=active` — *not implemented*


|                |                                                           |
| -------------- | --------------------------------------------------------- |
| Auth           | Practitioner login (Medtech or Entra, To be decided)      |
| Role           | `align_app`, `is_patient() = false`                       |
| Response       | List of `Encounter` rows, org-scoped automatically by RLS |
| Tables touched | `Encounter` (read only)                                   |


### `GET /clinician/sessions/{id}` — *not implemented*


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


### `POST /clinician/sessions/{id}/comments` — *not implemented*

Clinician free-text note — also not graph-driven (alongside mark-complete above).


|                |                                                      |
| -------------- | ---------------------------------------------------- |
| Auth           | Practitioner login (Medtech or Entra, To be decided) |
| Role           | `align_app`, `is_patient() = false`                  |
| Request        | `{ body: str }`                                      |
| Tables touched | `PractitionerComment` (insert)                       |


### `PUT /clinician/sessions/{id}/comments/{comment_id}` / `DELETE .../{comment_id}` — *not implemented*

Edit or remove a comment. Restricted to the comment's own author (`practitioner_id` must match the caller).


|                |                                                  |
| -------------- | ------------------------------------------------ |
| Auth           | Practitioner login, must be the comment's author |
| Role           | `align_app`, `is_patient() = false`              |
| Request (PUT)  | `{ body: str }`                                  |
| Tables touched | `PractitionerComment` (update/delete)            |


Note: the comments that are synced to the medtech are not updatable

---

## 3. Management API — *not implemented*

Designed surface only; none of `routers/organizations.py`,
`routers/practitioners.py` or `routers/admin.py` exist.

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

## 4. Demo (`routers/demo.py`) — *not implemented*

Same shape as /sessions but with /demo/sessions. The patient will be created with `patient.kind = DEMO` .
