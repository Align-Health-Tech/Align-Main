# Curated clinical evidence catalogues

These CSVs are the only URL inventory used by the LangChain tool named
`web_search`. Despite that public tool name, this is not a general internet
search: the tool ranks reviewed catalogue rows and fetches only the selected
Healthify or Health NZ pages.

## Files and load order

The order is part of the ranking contract:

1. `healthify_health_az_urls.csv` — columns `title,url,letter`
2. `healthnz_health_topics_urls.csv` — columns
   `title,url,path,parent_path,depth`

The loader consumes only `title` and `url`; additional export columns are
ignored. Files are read as BOM-compatible UTF-8. Catalogue file order followed
by row order is the final tie-break for equal BM25 scores, so do not casually
sort or reorder rows.

Only committed, non-placeholder HTTPS rows on these exact hosts are eligible:

- `healthify.nz`
- `www.healthnz.govt.nz`

Malformed URLs and all other hosts are rejected before ranking or fetching.

## Updating the catalogues

Replace a CSV only with a reviewed export, preserve its expected columns and
intentional row order, and include both CSVs in the same commit as any loader
contract change. Then run:

```bash
cd apps/api-server
./venv/bin/python -m unittest tests.test_curated_evidence_tool
./venv/bin/ruff check intelligence/tools.py tests/test_curated_evidence_tool.py
```

See [the API server README](../README.md#curated-clinical-evidence)
for ranking, fetching, attribution, and fallback behaviour.
