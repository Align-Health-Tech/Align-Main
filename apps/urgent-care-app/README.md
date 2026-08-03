# Align urgent-care demo

Single-page multilingual urgent-care intake backed by the existing FastAPI
session lifecycle.

## Behaviour

- Desktop (`>=1024px`): patient pane at 30% and clinician pane at 70%, with
  independent scrolling.
- Mobile/tablet: sticky Patient/Clinician toggle with Patient selected first.
- Patient UI languages: English (`en`), Korean (`ko`), and Simplified Chinese
  (`zh`).
- Consent and patient identity are frontend-owned. After identity is valid, the
  app creates the backend session and immediately submits the backend's
  canonical consent acceptance before showing the first clinical question.
- Clinical questions render directly from FastAPI `NextStep`. `kind="scale"`
  renders as a slider; it starts unanswered rather than at a midpoint, so an
  untouched control cannot submit a severity the patient never chose.
- One encounter is kept per browser tab in `sessionStorage`. Restart explicitly
  clears it.
- A first-run guide modal explains the demo. Dismissal is remembered in
  `localStorage` (`align-demo-guide-seen-v1`); the `?` button reopens it.

## The clinician pane is English-only

It is read by clinicians who do not speak the patient's language, so it never
renders `nativePrompt` or `nativeValue`. An answer with no English is reported
as a gap ("Not available in English") rather than shown in a language the reader
cannot use. Patient names are the sole exception.

Rows are built locally from the submitted answers, then their English is filled
in from the `mirror` field the backend returns on every session response
(`schemas/clinician_mirror.py`). The join key is `collect_target_id`, not the
answer text — once the classifier is ready it rewrites `chief_complaint` into an
English summary, so matching on the patient's original wording finds nothing.

Because `mirror` also comes back from `GET /sessions/{id}`, the clinician view
survives a page refresh. `encounter_summary` populates the AI summary card.

## Local development

From the repository root:

```bash
npm install
npm run generate --workspace=@align/generated-types
npm run dev
```

The UI is served at `http://localhost:3000`. Its same-origin Route Handler
forwards only the required session routes to:

```env
ALIGN_API_BASE_URL=http://localhost:8000
```

`ALIGN_API_BASE_URL` is server-only. The default above is used when it is not
set.

## Verification

```bash
npm run generate --workspace=@align/generated-types
npm run typecheck --workspace=urgent-care-app
npm run lint --workspace=urgent-care-app
npm run build --workspace=urgent-care-app
```

Generated contracts live in `packages/generated-types/src/api.ts` and must be
regenerated whenever the FastAPI OpenAPI schema changes.

## Source reuse

Patient presentation patterns, clinician cards, Align design tokens, locale
copy, the Align logo, body-diagram interaction, and SVGs were adapted from
`Align-Pilot-V2` commit `821010f`. Shorecare branding, legacy controllers,
dashboard routing, Supabase, tRPC, authentication, realtime, and printing were
not imported.
