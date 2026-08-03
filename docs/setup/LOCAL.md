# Local development setup

Prerequisites: **Docker Desktop**, **Node 20+** (npm), **Python 3.12+**.

---

## 1. Clone and install JS workspaces

```bash
git clone <repo-url> Align-Main
cd Align-Main
npm install
```

This installs Turborepo + workspace apps (`urgent-care-app`, `api-server` npm scripts).

Generate the frontend API contracts from the local FastAPI app:

```bash
npm run generate --workspace=@align/generated-types
```

The generator uses `apps/api-server/venv/bin/python`, so complete the Python
environment setup below before running it on a fresh clone.

---

## 2. Start Postgres

```bash
docker compose up -d --wait
```

| Setting | Value |
| ------- | ----- |
| Host | `localhost` |
| Port | `5432` |
| Database | `align` |
| User | `align_owner` |
| Password | `local_dev_only` |

Postgres **18** mounts data at `/var/lib/postgresql` (not `.../data`). If the container exits on start after an image upgrade, recreate the volume:

```bash
docker compose down -v && docker compose up -d --wait
```

---

## 3. Python API server (`apps/api-server`)

```bash
cd apps/api-server
python3 -m venv venv          # folder must be named `venv` (see package.json)
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # edit if needed
```

`.env` must include (SQLAlchemy form):

```env
DATABASE_URL=postgresql+psycopg://align_owner:local_dev_only@localhost:5432/align
```

---

## 4. Azure OpenAI Responses API

The API runtime and scripts invoked with `--real-azure` use Azure OpenAI.
Ordinary unit and graph tests mock this boundary and do not require Azure
credentials.

Set these values in `apps/api-server/.env`:

```env
AZURE_OPENAI_API_KEY=<resource-key>
AZURE_OPENAI_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
AZURE_MODEL_NAME=<gpt-5.4-deployment-name>
# Optional; defaults to 2025-04-01-preview
AZURE_OPENAI_API_VERSION=2025-04-01-preview
```

`AZURE_OPENAI_ENDPOINT` must be the exact resource endpoint shown by Azure.
`AZURE_MODEL_NAME` is the Azure **deployment name**, not necessarily the base
model ID. The client intentionally uses `AzureChatOpenAI` with the Responses
API, `reasoning_effort="low"`, a 60-second request timeout, and no SDK retries.
GPT-5.4 Responses does not accept a configurable `temperature` in this
integration.

For an end-to-end local session:

```bash
cd apps/api-server
./venv/bin/python scripts/cli_session.py --real-azure
```

Priority and red-flag Devise phases each perform one curated evidence tool
round; the tool may fetch up to three allowlisted catalogue pages in parallel.
See [the smoke and CLI guide](../../apps/api-server/scripts/README.md) for the
observable diagnostics.

---

## 5. Migrations (Alembic)

From `apps/api-server` with venv active and Postgres healthy:

```bash
alembic upgrade head
```

Expected chain:

```
base → 859d69d120fc (initial schema)
     → rls_roles_policies_001 (RLS)
     → add_intake_fact_display_001
     → summary_str_laterality_ck_001
     → intake_patient_scope_meds_001 (patient-scoped intake facts + encounter_medication)
     → simplify_flag_status_001 (drop unused Flag source/tier)
```

Check:

```bash
alembic current   # should show simplify_flag_status_001 (head)
```

**Do not** `alembic revision --autogenerate` for RLS — that migration is hand-written (`alembic/versions/rls_roles_and_policies.py`).

---

## 6. Verify the local database

From the repository root, the clone-to-proof flow is:

```bash
docker compose up -d --wait
source apps/api-server/venv/bin/activate
python scripts/verify_local_postgres.py
```

The verifier reads `DATABASE_URL` from the environment or
`apps/api-server/.env` and refuses to connect to a non-local host. Its
throwaway engine/session applies Alembic to head, checks the schema contract,
and commits then reloads three complete states through the SQLAlchemy models:
the original sore-throat fixture plus the real-Azure localised-wrist and
non-localised-fever fixtures. The wrist case includes its body-structure,
allergy, and active CIRCULATION flag rows. `fhir_display` carries the fixture
topic for this round-trip without claiming that a FHIR coding was resolved.
The fever case asserts that no body-structure, intake-fact, or flag rows are
created. Practitioner, patient, and admin RLS checks run against these same
fixture rows using the real database roles. A successful run prints named
`PASS` results and removes all generated rows.

To retain the generated organizations, patients, encounters, body structures,
intake facts, and flags for inspection, run:

```bash
python scripts/verify_local_postgres.py --keep-data
```

The retained row IDs are printed at the end. LangGraph checkpoint-table setup
and `PostgresSaver` are not required for this verification.

---

## 7. RLS role passwords (local only)

Roles `align_app`, `align_engine`, `align_admin` are created by the RLS migration **without** passwords (secrets stay out of git). Set them once:

```bash
# from repo root — container name is align-main-postgres-1
docker compose exec postgres psql -U align_owner -d align -c "
ALTER ROLE align_app WITH PASSWORD 'local_dev_password';
ALTER ROLE align_engine WITH PASSWORD 'local_dev_password';
ALTER ROLE align_admin WITH PASSWORD 'local_dev_password';
"
```

---

## 8. LangGraph checkpoint tables (optional until engine is wired)

Checkpoint tables are **not** created by Alembic. After installing deps:

```bash
cd apps/api-server
source venv/bin/activate
python -c "
from langgraph.checkpoint.postgres import PostgresSaver
with PostgresSaver.from_conn_string(
    'postgresql://align_owner:local_dev_only@localhost:5432/align'
) as cp:
    cp.setup()
"
```

Use plain `postgresql://` here (not `postgresql+psycopg://`). Needs package `langgraph-checkpoint-postgres`.

After `setup()`, a follow-up migration may be needed to attach `organization_id` + RLS to checkpoint tables (skipped on first RLS run if tables were missing).

---

## 9. Run everything

From **repo root**:

```bash
npm run dev
```

This:

1. Starts Postgres (`docker compose up -d --wait`)
2. Runs Turbo `dev` for `urgent-care-app` (Next.js) and `api-server` (uvicorn on `:8000`)

Apps only (Postgres already up):

```bash
npm run dev:apps-only
```

| Service | URL |
| ------- | --- |
| API health | http://localhost:8000/health |
| API docs | http://localhost:8000/docs |
| Urgent care UI | http://localhost:3000 (Next default) |

The urgent-care app proxies its browser requests through a same-origin Next.js
Route Handler. It reads the server-only variable below and defaults to the
local API URL shown above:

```env
ALIGN_API_BASE_URL=http://localhost:8000
```

Patient consent, identity, and `en` / `ko` / `zh` UI copy are frontend-owned.
The existing FastAPI session lifecycle remains unchanged; after identity entry,
the UI creates a session and submits its canonical consent response.

---

## Docs to read next

- [DATABASE.md](../database/DATABASE.md) — schema
- [RLS.md](../database/RLS.md) — roles & policies
- [APISTRUCTURE.md](../apps/api-server/APISTRUCTURE.md) — target API surface
- [REPOSITORYRULE.md](../repository-rule/REPOSITORYRULE.md) — conventions
