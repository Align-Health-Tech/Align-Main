"""
FastAPI entrypoint. Routers get added here as they're built — see
apps/api-server/README.md for the full planned endpoint surface
(session, clinician, admin, demo).
"""
from fastapi import FastAPI

from routers import clinician, session

app = FastAPI(title="Align API", version="0.1.0")

app.include_router(session.router)
app.include_router(clinician.router)


@app.get("/health")
def health() -> dict:
    """Confirms the process is up and (separately) that DATABASE_URL
    resolves — doesn't check the DB connection itself yet."""
    return {"status": "ok"}


# Future routers (M7+):
# from routers import admin, demo
# app.include_router(admin.router)
# app.include_router(demo.router)
