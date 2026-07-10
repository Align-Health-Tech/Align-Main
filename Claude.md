# Align-Main — Agent guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

---

## 1. Documentation is source of truth

Always **read and strictly follow** the relevant docs under `/docs` before changing code. Keep docs and code in sync.

| Concern | Doc |
| ------- | --- |
| Schema / tables / columns | [`docs/database/DATABASE.md`](docs/database/DATABASE.md) |
| RLS roles & policies | [`docs/database/RLS.md`](docs/database/RLS.md) |
| API surface (target design) | [`docs/apps/api-server/APISTRUCTURE.md`](docs/apps/api-server/APISTRUCTURE.md) |
| Repo conventions | [`docs/repository-rule/REPOSITORYRULE.md`](docs/repository-rule/REPOSITORYRULE.md) |
| External-system ideation | [`docs/structures/structure.md`](docs/structures/structure.md) |

**Rules:**

- Before DB work: read `DATABASE.md` and `RLS.md`. Do not invent columns, enums, or access patterns that contradict them.
- Before API / router work: read `APISTRUCTURE.md`.
- When code changes a contract (schema, RLS, endpoints, naming): **update the matching doc in the same change**.
- If docs and code disagree: stop, surface the conflict, and ask which side to trust — do not silently pick.
- Do not leave docs stale after a deliberate design change.

---

## 2. Think before coding

Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

---

## 3. Simplicity first

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

---

## 4. Surgical changes

Touch only what you must. Clean up only your own mess.

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that **your** changes made unused.
- Don't remove pre-existing dead code unless asked.

**Test:** Every changed line should trace directly to the user's request.

---

## 5. Goal-driven execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

- "Add validation" → write tests for invalid inputs, then make them pass
- "Fix the bug" → write a test that reproduces it, then make it pass
- "Refactor X" → ensure tests pass before and after

For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

These guidelines are working if: fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, clarifying questions come before implementation, and docs stay aligned with code.
