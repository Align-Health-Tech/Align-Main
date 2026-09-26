# FastAPI + LangGraph engine for the Align urgent-care demo.
#
#   docker build -f apps/api-server/Dockerfile -t align-api apps/api-server
#
# Runs with NO public ingress on Vercel: the `api` service in vercel.json has no
# rewrite, and only the `web` service reaches it, over a service binding.
# Nothing here does its own authentication — see routers/clinician.py
# ("Auth ... deferred to M7") — so this must never be given a public route.
#
# Required env: AZURE_OPENAI_API_KEY, AZURE_MODEL_NAME, AZURE_OPENAI_ENDPOINT
# Optional:     AZURE_OPENAI_API_VERSION (defaults to 2025-04-01-preview)

FROM python:3.14-slim AS runtime

# PYTHONUNBUFFERED so uvicorn logs reach the runtime log stream promptly
# rather than sitting in a pipe buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Separate layer so image rebuilds skip reinstalling ~90 packages on code edits.
# psycopg is installed as psycopg-binary, so no libpq build toolchain is needed.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Belt and braces: .dockerignore already excludes these, but a stale local venv
# copied into the image would shadow site-packages and break the import path.
RUN rm -rf venv .venv tests/transcripts

RUN useradd --create-home --uid 1000 align
USER align

EXPOSE 8000

# Single worker is mandatory, not a default: engine/checkpointer.py uses
# LangGraph's MemorySaver and services/session_store.py holds sessions in the
# process, so a second worker would serve requests that cannot see the session.
# Vercel sets PORT from the project settings; 8000 is the local default.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
