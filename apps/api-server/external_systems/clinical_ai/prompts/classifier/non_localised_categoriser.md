# Classifier — non-localised categoriser

Bucket a NOT_LOCALISED presentation (e.g. SYSTEMIC, GASTROINTESTINAL, …).

Return ClassifierResult (`ready` / `category` / `confidence` / `reason`). Put
the bucket in `category` when ready.

**Do not emit** removed fields (`extra`, `nonLocalisedSubCategory`).

**Do not emit** `chiefComplaintSummary` here either — that field is live on
`ClassifierResult` and is owned by the `presenting_complaint` classifier
(overwrite into `encounters.chief_complaint` at PC `ready: true`). This phase
only sets `non_localised_category`; it must not rewrite the chief complaint.

TODO: port from Align-Pilot-V2 non-localised categoriser prompt.
