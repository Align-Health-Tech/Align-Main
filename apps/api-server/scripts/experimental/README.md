# Experimental smokes (not CI)

Probes under this folder are exploratory Azure runs.
Production smoke suites stay in `scripts/smoke_*`.

- `smoke_devise_empty_pool` — Devise with empty candidate_pool
- `smoke_devise_open` — open Devise (no registry ids)
- `smoke_qg_stripped_hints` — QG without suggestion fields
- `smoke_qg_comorbid_freq` — comorbidities option frequency using
  model-default variation; GPT-5.4 Responses does not accept `temperature`
- `prompts/` — unused exploratory prompts
