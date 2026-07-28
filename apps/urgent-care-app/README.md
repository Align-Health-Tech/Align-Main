# Align urgent-care demo

Single-page multilingual urgent-care intake backed by the existing FastAPI
session lifecycle.

## Behaviour

- Desktop (`>=1024px`): patient pane at 42% and clinician pane at 58%, with
  independent scrolling.
- Mobile/tablet: sticky Patient/Clinician toggle with Patient selected first.
- Patient UI languages: English (`en`), Korean (`ko`), and Simplified Chinese
  (`zh`).
- Consent and patient identity are frontend-owned. After identity is valid, the
  app creates the backend session and immediately submits the backend's
  canonical consent acceptance before showing the first clinical question.
- Clinical questions render directly from FastAPI `NextStep`.
- One encounter is kept per browser tab in `sessionStorage`. Restart explicitly
  clears it.

The backend is unchanged for this demo. Consequently the clinician pane is a
live mirror of answers submitted in the current browser tab, not a backend
clinician-detail read model. Choice answers use `en_label ?? label`; non-English
free text retains patient wording and is labelled as untranslated. The
backend's internal AI summary is intentionally not exposed.

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
npm run test --workspace=urgent-care-app
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
