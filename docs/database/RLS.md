# Align RLS Design

---

## Foundation


| Role           | Used by                                                                                                             | Table access                                                                                                                                                                                                                                                                                                                                      |
| -------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `align_app`    | Patient and practitioner request traffic (everything in §1–5, §7)                                                   | Normal GRANT + RLS policy per table below                                                                                                                                                                                                                                                                                                         |
| `align_engine` | The engine's own automatic logging writes (AI calls, audit trail) — never a human session                           | **INSERT-only** on `audit_logs`, `lilly_ai_interactions`. No SELECT/UPDATE/DELETE — the engine writes a log row and never reads it back                                                                                                                                                                                                           |
| `align_admin`  | Align's own internal admin/ops, via a separate internal auth path — not reachable from the patient/practitioner API | **Read-only** across every table in §1–5, §6 — cross-organization, no `organization_id` filter (dashboard needs to see across all clinics). **Read/write** on the §6 admin-only tables specifically. No `BYPASSRLS` — still goes through explicit policy, same as everything else, so RLS stays consistently enforced/auditable across every role |


**Session variables** (set by the FastAPI backend via `SET LOCAL`, only relevant to `align_app`):


| Variable                        | Meaning                                                       |
| ------------------------------- | ------------------------------------------------------------- |
| `app.current_organization_id()` | Tenant scope for this request                                 |
| `app.current_encounter_id()`    | Set only for patient-role requests                            |
| `app.is_patient()`              | `true` for QR-token sessions, `false` for practitioner logins |


---

## 1. `organizations`


| Role                                  | Operation | Scope                                                       |
| ------------------------------------- | --------- | ----------------------------------------------------------- |
| `align_app` (patient or practitioner) | Read      | Own organization only                                       |
| `align_app`                           | Write     | **None**                                                    |
| `align_admin`                         | Read      | All organizations — dashboard needs cross-clinic visibility |


---

## 2. `patients`


| Role                       | Operation  | Scope                                                                                                                                          |
| -------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `align_app` (practitioner) | Read/write | Any patient in own organization                                                                                                                |
| `align_app` (patient)      | Read/write | Only their own record, resolved via their current encounter (patients hold no direct `patient_id` credential — QR token → encounter → patient) |
| `align_admin`              | Read       | Any patient, any organization                                                                                                                  |


---

## 3. `consents`


| Role                       | Operation  | Scope                                                                             |
| -------------------------- | ---------- | --------------------------------------------------------------------------------- |
| `align_app` (practitioner) | Read/write | None                                                                              |
| `align_app` (patient)      | Read/write | Only their own consent records (needed to submit privacy policy / T&C acceptance) |
| `align_admin`              | Read       | Any organization                                                                  |


---

## 4. `encounters`, `body_structures`, `radiation_sites`, `flags`, `intake_fact_items`

The core encounter-scoped group — all clinical detail for one session.


| Role                       | Operation  | Scope                                                                                                                                  |
| -------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `align_app` (practitioner) | Read/write | Everything in own organization                                                                                                         |
| `align_app` (patient)      | Read/write | Only rows belonging to their current, active encounter (`radiation_sites` scoped one join further, via `body_structures.encounter_id`) |
| `align_admin`              | Read       | Any encounter, any organization                                                                                                        |


---

## 5. `practitioners`, `practitioner_comments`


| Role                       | Operation  | Scope                                                                        |
| -------------------------- | ---------- | ---------------------------------------------------------------------------- |
| `align_app` (practitioner) | Read/write | Own organization                                                             |
| `align_app` (patient)      | None       | None                                                                         |
| `align_admin`              | Read       | Any organization — includes reading clinician notes, for QA/dashboard review |


---

## 6. `audit_logs`, `lilly_ai_interactions`, `surveys`


| Role                                  | Operation                                           | Scope                                               |
| ------------------------------------- | --------------------------------------------------- | --------------------------------------------------- |
| `align_app` (patient or practitioner) | None                                                | **None**                                            |
| `align_engine`                        | Insert only (`audit_logs`, `lilly_ai_interactions`) | Any organization                                    |
| `align_admin`                         | Read/write                                          | **Cross-organization, no `organization_id` filter** |


### `survey_responses`


| Role                       | Operation | Scope                                                      |
| -------------------------- | --------- | ---------------------------------------------------------- |
| `align_app` (patient)      | Write     | Only their own submission, tied to their current encounter |
| `align_app` (practitioner) | None      | None                                                       |
| `align_admin`              | Read      | Cross-organization                                         |


## 7. `checkpoints`, `checkpoint_writes`, `checkpoint_blobs`, `checkpoint_migrations`


| Role                       | Operation  | Scope                                                                                       |
| -------------------------- | ---------- | ------------------------------------------------------------------------------------------- |
| `align_app` (patient)      | Read/write | Only their own thread (`thread_id = current_encounter_id()`), while their session is active |
| `align_app` (practitioner) | —          | Not needed — practitioners read `encounters`/`body_structures`/etc. instead                 |


**No `organization_id IS NULL` exception** — see §8.

---

## 8. Align admin auth

To be decided. Entra MFA looks like a good option