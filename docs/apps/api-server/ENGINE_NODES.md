# Engine nodes & helpers — design index

Short “why” notes for finished, Azure-smoke-verified pieces. Not a
restatement of code (see docstrings / prompts). Add a row when each M5
slice ships — do not pre-document unfinished work.

Companion: [USERFLOW.md](../../structures/USERFLOW.md),
[prompts/README.md](../../../apps/api-server/external_systems/clinical_ai/prompts/README.md).

---

## Graph nodes

LangGraph nodes under `engine/nodes/` (plus Devise+QG **phases** owned by a
node — not separate topology entries). Each may `interrupt()` with a
`NextStep`.

| Name | Kind | Shape | Design decisions (why) | Prompts / smoke |
| ---- | ---- | ----- | ---------------------- | --------------- |
| `presenting_complaint` | Graph node | (1) Free-text gate → (2) classify → clarify until `ready: true` → LOCALISED / NOT_LOCALISED | Classifier does **not** emit clarify text (3-agent rule: Devise+QG owns clarify). At `ready: true`, `chief_complaint` ← `chiefComplaintSummary` (`source: "ai_summary"`); raw words stay in `messages`, not a separate DB column. | `classifier/presenting_complaint.md` · smokes: `smoke_presenting_complaint_classifier/`, `smoke_presenting_complaint_clarify/` |
| `presenting_complaint_clarify` | Devise+QG phase (owned by PC node) | `devise_then_generate` when PC `ready: false` | Empty registry pool — invent topics from routing gap. Region options 1:1 `majorRegion` (Face/Arm/Leg/Torso); no “arm or leg” groups. `en_prompt`/`en_label` only if `session_language != "en"`. | `devise_and_prioritise/presenting_complaint_clarify.md`, `question_generation/presenting_complaint_clarify.md` |
| `non_localised_detail` | Graph node | (1) Six-bucket categoriser + clarify until `non_localised_category` set → (2) timing / severity / functional chips → priority | Bucket `category` ≠ LOCALISED/NOT_LOCALISED; apply via `prompt_name="non_localised_categoriser"` only. **`run_classifier` nulls PC-only fields** (`chiefComplaintSummary`, anatomy, supplement) so NL cannot overwrite complaint text. **Max 3 clarify rounds in code:** increment `non_localised_clarify_rounds` only on enqueue; after 3, skip classifier and force-commit lean → else `SYSTEMIC`. Round count in context is informational, not the safety net. | `classifier/non_localised_categoriser.md` · smoke: `smoke_non_localised_categoriser/` · tests: `test_nl_clarify_rounds.py` |
| `non_localised_clarify` | Devise+QG phase (owned by NL node) | When categoriser `ready: false` | Options exactly `Yes` / `No` / `I don't know` (validator-enforced); no `"Other"`. Feature presence/absence only. `en_*` only if not English. | `devise_and_prioritise/non_localised_clarify.md`, `question_generation/non_localised_clarify.md` |
| `priority_questions` | Graph node (Devise+QG) | Rank registry priority targets → batch questions → redflag | **Prefill-and-confirm:** target ids present as keys in `known_collect_values` rank lower but stay in pool; QG sets `default_value` / `default_values` from those values. Never omit solely because known. Comorbidities: `"None of these"`, never `"Other"`. Pregnancy only when sex-filtered into pool. | `devise_and_prioritise/priority_questions.md`, `question_generation/priority_questions.md` · smoke: `smoke_priority_questions/` |
| `redflag_screening` | Graph node (Devise+QG) | After priority → optional | Full `REDFLAG_TARGETS` pool every time (`{subcategory, clinical_hint}`; **not** locality-filtered). Empty Devise OK. Backend `normalize_redflag_subcategory` clamps topics onto the 6 labels (unknown → `OTHER`). QG: flat `yes_no` only (validator). `is_red_flag=True` stamped in code from phase, not model. Prompt nudges web_search when uncertain (not forced `tool_choice`). No sub-question chains. | `devise_and_prioritise/redflag_screening.md`, `question_generation/redflag_screening.md` · smoke: `smoke_redflag_screening/` |

**NL force-commit detail:** primary = `non_localised_category_lean` (best-fit `category` on `ready: false`); fallback = `SYSTEMIC`.

---

## Helpers (not nodes)

Shared utilities nodes call. Not in the graph topology.

| Name | Where | Role | Design decisions (why) |
| ---- | ----- | ---- | ---------------------- |
| `apply_classifier_result` | `engine/helpers/apply_classifier_result.py` | Map ready `ClassifierResult` → state updates | Branches on `prompt_name`: PC → `presentation_category` + optional ai_summary / anatomy / supplement; NL categoriser → `non_localised_category` **only**. Prevents bucket labels corrupting `presentation_category`. |
| `apply_answers` | `engine/helpers/apply/` | Map resume answers → state updates | Package: `answers.py` dispatcher + phase mappers (`body_diagram`, `presenting_complaint`, `detail`, `priority`, `redflag`, `ice`). Import via `from engine.helpers.apply import apply_answers`. |
| `build_agent_context` | `engine/helpers/agent_bridge.py` | `SessionState` → small LLM context dict | Projection only — omit interrupt plumbing. Conversation via `conversation_from_state` separately. Includes NL rounds/lean and `known_collect_values` for QG prefill (key present ⇒ already known). |
| `get_eligible_targets` / `targets_for_session_phase` | `external_systems/clinical_ai/registry.py` | Sex + locality filter on priority/optional pools | `targets_for_session_phase` maps graph phase → filtered targets (shared by Devise pool + QG eligible). Already-known status is via `known_collect_values` on agent context, not these functions. Pilot-parity: e.g. `onset_circumstance` LOCALISED-only; optional `past_history` LOCALISED-only; `family_history` / `weight_change` / `social_history` NOT_LOCALISED-only. |
| `body_diagram_catalogue` (`resolve_prefill_candidates` / `resolve_coding`) | `engine/static/body_diagram_catalogue/` | Classifier sites → SVG prefill / `CodedField` | Two tables: `PREFILL_MAPPINGS` (region_id may repeat across views) vs `REGION_CODINGS` (unique id → coding). `surface="unknown"` → first body_part+side catalogue hit, not a hardcoded surface. |
| `onset_timing` | `engine/static/onset_timing.py` | Shared timing chips for `loc_onset` / `nl_onset` | Shorecare/Pilot canons: Last 24h / 48h / 1 week / &gt;1 week. Stored as `onset_circumstance` with `source: "option"`. |

---

## Not in this doc yet

| Pending |
| ------- |
| `localised_detail` (body diagram + severity/timing) — verified in tests; add row when documenting that slice explicitly |
| optional · ice · review · complete |
