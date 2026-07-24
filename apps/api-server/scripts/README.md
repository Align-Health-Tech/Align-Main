# Smoke scripts + CLI

Each smoke lives in its own folder:

```
scripts/<smoke_name>/<smoke_name>.py
scripts/<smoke_name>/results/vNNN_results_YYYY-MM-DD_HHMMSS.txt
```

Results are **never overwritten** — each run writes a new versioned file via
`_smoke_results.next_result_path`.

Legacy flat paths (`scripts/smoke_*.py`, `scripts/results/`) are retired.

## Interactive session CLI (M6)

```
./venv/bin/python scripts/cli_session.py
./venv/bin/python scripts/cli_session.py --session_language ko --patient_sex male
```

Walks consent → graph → survey → clinician complete with mocked clinical_ai
by default. The default path makes no Azure request and performs no catalogue
URL fetch. Use `--real-azure` only for local spot checks; it requires the Azure
variables described in [local setup](../../../docs/setup/LOCAL.md#4-azure-openai-responses-api).
Not for CI.

In a real-Azure session, the priority and red-flag Devise phases each invoke
`web_search` exactly once and may fetch zero to three ranked sources in
parallel. Optional and clarification phases do not call the tool. The CLI
signal summary shows the tool query/call. The dedicated
`smoke_priority_questions` and `smoke_redflag_screening` scripts provide the
full evidence diagnostics: query, ranked URLs and BM25 scores, successful and
failed fetches, per-source latency, parallel batch latency, and final candidate
attribution.

```bash
./venv/bin/python scripts/smoke_priority_questions/smoke_priority_questions.py
./venv/bin/python scripts/smoke_redflag_screening/smoke_redflag_screening.py
```

Choice questions (yes/no, chips, body-diagram regions, survey) use an ↑↓
keyboard menu (Enter to select, Space to toggle multi-select). Free text is
still typed.
