# Smoke scripts

Each smoke lives in its own folder:

```
scripts/<smoke_name>/<smoke_name>.py
scripts/<smoke_name>/results/vNNN_results_YYYY-MM-DD_HHMMSS.txt
```

Results are **never overwritten** — each run writes a new versioned file via
`_smoke_results.next_result_path`.

Legacy flat paths (`scripts/smoke_*.py`, `scripts/results/`) are retired.
