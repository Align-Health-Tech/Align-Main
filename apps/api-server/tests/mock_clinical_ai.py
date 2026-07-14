"""CI doubles for clinical_ai — patch engine.helpers.agent_bridge (no Azure).

Mock rules (locked for M5):
- Order-based classifier scripts → side_effect list / scripted returns
- Phase/prompt_name Devise+QG → side_effect=function branching on phase
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional
from unittest.mock import patch

from schemas.clinical_ai_io import (
    ClassifierInput,
    ClassifierResult,
    QuestionGenerationInput,
    QuestionGenerationResult,
    ReviewSummaryResult,
    TranslationResult,
)
from schemas.question_fields import QuestionField, QuestionOption
from schemas.topic_candidates import TopicCandidate
from tests.mock_clinical_ai_fixtures import QUESTIONS_BY_PHASE, TOPICS_BY_PHASE

_BRIDGE = "engine.helpers.agent_bridge"


class ClinicalAiMock:
    """Deterministic stand-in matching former in-node fake Q IDs / heuristics."""

    def __init__(self) -> None:
        self.classifier_calls = 0
        self.nl_classifier_calls = 0
        self.clarify_qg_calls = 0
        self.nl_clarify_qg_calls = 0
        self.devise_calls_by_phase: dict[str, int] = defaultdict(int)
        self.qg_calls_by_phase: dict[str, int] = defaultdict(int)
        self.nurse_calls = 0
        self.translate_calls = 0
        self._pc_script: list[ClassifierResult] | None = None
        self._nl_script: list[ClassifierResult] | None = None

    def reset(self) -> None:
        self.__init__()

    def set_classifier_script(self, results: list[ClassifierResult]) -> None:
        self._pc_script = list(results)

    def set_nl_classifier_script(self, results: list[ClassifierResult]) -> None:
        self._nl_script = list(results)

    @property
    def fake_classifier_call_count(self) -> int:
        return self.classifier_calls

    @property
    def fake_clarify_qg_call_count(self) -> int:
        return self.clarify_qg_calls

    @property
    def fake_nl_classifier_call_count(self) -> int:
        return self.nl_classifier_calls

    @property
    def fake_nl_clarify_qg_call_count(self) -> int:
        return self.nl_clarify_qg_calls

    @property
    def fake_priority_qg_call_count(self) -> int:
        return self.qg_calls_by_phase["priority_questions"]

    @property
    def fake_redflag_qg_call_count(self) -> int:
        return self.qg_calls_by_phase["redflag_screening"]

    @property
    def fake_optional_qg_call_count(self) -> int:
        return self.qg_calls_by_phase["optional_questions"]

    @property
    def fake_ice_qg_call_count(self) -> int:
        return self.qg_calls_by_phase["ice"]

    @property
    def fake_nurse_call_count(self) -> int:
        return self.nurse_calls

    @property
    def fake_translate_call_count(self) -> int:
        return self.translate_calls

    def run_classifier(self, input: ClassifierInput) -> ClassifierResult:
        if input.prompt_name == "presenting_complaint":
            self.classifier_calls += 1
            if self._pc_script is not None:
                idx = min(self.classifier_calls - 1, len(self._pc_script) - 1)
                return self._pc_script[idx]
            return _heuristic_pc_classifier(input)

        if input.prompt_name == "non_localised_categoriser":
            self.nl_classifier_calls += 1
            if self._nl_script is not None:
                idx = min(self.nl_classifier_calls - 1, len(self._nl_script) - 1)
                return self._nl_script[idx]
            return ClassifierResult(
                ready=True, category="SYSTEMIC", confidence=0.9, reason="mock default"
            )

        raise ValueError(f"unexpected classifier prompt_name: {input.prompt_name!r}")

    def run_devise_and_prioritise(
        self, phase: str, context: dict
    ) -> list[TopicCandidate]:
        self.devise_calls_by_phase[phase] += 1
        return list(TOPICS_BY_PHASE.get(phase, []))

    def run_question_generation(
        self, input: QuestionGenerationInput
    ) -> QuestionGenerationResult:
        phase = input.prompt_name
        self.qg_calls_by_phase[phase] += 1

        if phase == "presenting_complaint_clarify":
            self.clarify_qg_calls += 1
            n = self.clarify_qg_calls
            return QuestionGenerationResult(
                reason="mock clarify",
                questions=[
                    QuestionField(
                        id=f"pc_clarify_{n}",
                        kind="single_choice",
                        prompt=f"Clarify round {n}: which best describes this?",
                        personalization_note="mock clarify",
                        collect_target_id="chief_complaint_clarify",
                        options=[
                            QuestionOption(
                                value="body_part",
                                label="Pain or problem in a body part",
                            ),
                            QuestionOption(
                                value="whole_body",
                                label="Whole-body / systemic symptoms",
                            ),
                            QuestionOption(value="Other", label="Other"),
                        ],
                    )
                ],
            )

        if phase == "non_localised_clarify":
            self.nl_clarify_qg_calls += 1
            n = self.nl_clarify_qg_calls
            return QuestionGenerationResult(
                reason="mock nl clarify",
                questions=[
                    QuestionField(
                        id=f"nl_clarify_{n}",
                        kind="single_choice",
                        prompt=(
                            f"Non-localised clarify {n}: any fever, fatigue, "
                            "or whole-body symptoms?"
                        ),
                        personalization_note="mock nl clarify",
                        collect_target_id="non_localised_clarify",
                        options=[
                            QuestionOption(value="Yes", label="Yes"),
                            QuestionOption(value="No", label="No"),
                            QuestionOption(
                                value="I don't know", label="I don't know"
                            ),
                        ],
                    )
                ],
            )

        questions = QUESTIONS_BY_PHASE.get(phase)
        if questions is None:
            raise ValueError(f"unexpected QG prompt_name: {phase!r}")
        return QuestionGenerationResult(
            reason=f"mock {phase}", questions=list(questions)
        )

    def run_nurse_review_summary_agent(self, context: dict) -> ReviewSummaryResult:
        self.nurse_calls += 1
        cc = (context.get("chief_complaint") or {}).get("text") or "unspecified complaint"
        cat = context.get("presentation_category") or "UNKNOWN"
        return ReviewSummaryResult(summary=f"Patient reports {cc} ({cat}).")

    def translate_to_english(
        self, source_text: str, source_lang: Optional[str] = None
    ) -> TranslationResult:
        self.translate_calls += 1
        return TranslationResult(
            en_text=f"[en] {source_text}",
            detected_lang=source_lang,
        )


def patch_clinical_ai(mock: ClinicalAiMock):
    """Start patches on agent_bridge; caller must stop / addCleanup."""
    targets = (
        ("run_classifier", mock.run_classifier),
        ("run_devise_and_prioritise", mock.run_devise_and_prioritise),
        ("run_question_generation", mock.run_question_generation),
        ("run_nurse_review_summary_agent", mock.run_nurse_review_summary_agent),
        ("translate_to_english", mock.translate_to_english),
    )
    started = []
    for name, fn in targets:
        p = patch(f"{_BRIDGE}.{name}", side_effect=fn)
        p.start()
        started.append(p)
    return started


class MockClinicalAiTestCase:
    """Mixin: setUp installs ClinicalAiMock on agent_bridge."""

    ai: ClinicalAiMock

    def setUp(self) -> None:  # type: ignore[override]
        self.ai = ClinicalAiMock()
        for p in patch_clinical_ai(self.ai):
            self.addCleanup(p.stop)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _heuristic_pc_classifier(input: ClassifierInput) -> ClassifierResult:
    text = ""
    cc = (input.context or {}).get("chief_complaint") or {}
    if isinstance(cc, dict):
        text = (cc.get("text") or "").lower()
    if not text:
        for msg in input.conversation or []:
            if isinstance(msg, dict) and msg.get("role") == "user":
                text = str(msg.get("content") or "").lower()
                break

    if any(w in text for w in ("wrist", "ankle", "knee", "shoulder", "back")):
        return ClassifierResult(
            ready=True,
            category="LOCALISED",
            confidence=0.95,
            reason="body part named",
            extra={"localisedAnatomySites": _fake_localised_sites(text)},
        )
    if any(w in text for w in ("fever", "tired", "fatigue", "unwell")):
        return ClassifierResult(
            ready=True,
            category="NOT_LOCALISED",
            confidence=0.9,
            reason="systemic wording",
        )
    return ClassifierResult(ready=False, reason="need more detail")


def _fake_localised_sites(text: str) -> list[dict]:
    if "wrist" in text:
        side = "left" if "left" in text else "right"
        return [
            {
                "bodyPart": "wrist",
                "side": side,
                "surface": "front",
                "majorRegion": "arm",
                "confidence": 0.95,
                "evidence": "mock",
            }
        ]
    if "ankle" in text:
        side = "left" if "left" in text else "right"
        return [
            {
                "bodyPart": "ankle",
                "side": side,
                "surface": "front",
                "majorRegion": "leg",
                "confidence": 0.9,
                "evidence": "mock",
            }
        ]
    return []
