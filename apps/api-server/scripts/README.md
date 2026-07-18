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
by default (`--real-azure` for spot checks). Not for CI.

Choice questions (yes/no, chips, body-diagram regions, survey) use an ↑↓
keyboard menu (Enter to select, Space to toggle multi-select). Free text is
still typed.
