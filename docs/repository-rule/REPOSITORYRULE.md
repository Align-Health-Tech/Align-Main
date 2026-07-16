# Contributing to Align

## 1. Code style

**Python:**

- Type hints everywhere; Pydantic models for anything crossing a boundary (API request/response, LangGraph state, provider interfaces)
- No bare `except:` — catch what you expect, let the rest surface
- `black` + `ruff` — for pretty code and strict code convention checks
- **Named `Literal` aliases, not inline.** Do not put `Literal["…"]` (or `Optional[Literal["…"]]`) directly on a field, parameter, or return type. Define a named alias in **`schemas/literals.py`** (the single source of truth for shared vocabularies), then import it:

  ```python
  # good
  from schemas.literals import FreeTextPolicy

  class CollectTarget(BaseModel):
      free_text_policy: Optional[FreeTextPolicy] = None

  # bad — inline, or redefined outside schemas/literals.py
  class CollectTarget(BaseModel):
      free_text_policy: Optional[Literal["avoid", "optional_other"]] = None
  ```

  Shared mappings between vocabularies (e.g. session phase → `CollectPhase`) stay next to the model that uses them (`schemas/collect_targets.py`); the `Literal` alias itself always lives in `schemas/literals.py`.

**Both:** no `console.log`/`print` debug statements left in merged code. No commented-out code blocks — delete it, git remembers.

---

## 2. Naming conventions

- Tables: When possible, make it directly equivalent to the table name.
- Variables and classes: Use clear, descriptive names that make their purpose obvious. Follow language conventions for naming style: use `snake_case` for Python, `camelCase` for TypeScript, and keep abbreviations or alternative spellings (like `organization_id` vs `organisation_id`) consistent within a project. For IDs and foreign keys, always prefer patterns like `organization_id` unless a strong reason exists to do otherwise. Use names that match existing terminology in the database or codebase when possible.
- **Private / internal helpers (Python):** A leading `_` means the symbol is **internal-only** — not part of the module’s public surface; callers outside the defining file must not import it. Prefer grouping these at the **bottom** of the file under an `# Internal helpers` section (private, internal helper), so the public API stays readable above. Do not prefix something that is intentionally part of the public contract even if it currently has zero callers (leave a short `# used once …` / deferred-use comment instead).

---

## 3. RLS aware code

Always refer to `docs/database/RLS.md` and `docs/database/DATABASE.md` before touching any database related code.

---

## 4. Documentations

All documentations sit under `/docs`. They must be updated when any relevant code changes.
