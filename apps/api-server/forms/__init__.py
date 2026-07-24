"""Router-level deterministic forms (consent / survey) — outside the graph.

Called by ``services/session_lifecycle``. Wrap into NextStep via
``engine.helpers.next_step``:

- Consent: ``build_next_step_raw(0, build_consent_questions(), phase="consent")``
- Survey: ``build_next_step(state, build_survey_questions(), phase="survey")``

See ``docs/structures/ROUTER_SPEC.md``.
"""
from forms.consent import build_consent_questions
from forms.survey import build_survey_questions

__all__ = ["build_consent_questions", "build_survey_questions"]
