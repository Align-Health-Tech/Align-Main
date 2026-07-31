"""Clinician mirror on the session responses.

The mirror is the only path by which the clinician pane sees English for patient
free text — the frontend can localise options and yes/no on its own, but a typed
sentence is only translated server-side.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from engine.session_state_mappers import map_patient_answers
from main import app
from schemas.clinician_mirror import build_clinician_mirror
from schemas.question_fields import QuestionField, QuestionOption
from schemas.session_states import SessionState
from services.session_lifecycle import lifecycle
from services.session_store import store
from tests.mock_clinical_ai import MockClinicalAiTestCase

_KO_COMPLAINT = "머리가 너무 아파서 왔어요"


class TestBuildClinicianMirror(unittest.TestCase):
    """Projection only — no HTTP, no graph."""

    def test_none_state_gives_empty_mirror(self) -> None:
        mirror = build_clinician_mirror(None)
        self.assertEqual(mirror.fields, [])
        self.assertIsNone(mirror.encounter_summary)

    def _state(self, **kwargs) -> SessionState:
        base = dict(
            session_id="s1",
            patient_id="p1",
            organization_id="o1",
            session_language="ko",
        )
        base.update(kwargs)
        return SessionState(**base)

    def test_free_text_carries_en_text(self) -> None:
        mirror = build_clinician_mirror(
            self._state(
                chief_complaint={
                    "text": _KO_COMPLAINT,
                    "en_text": "I came in with a bad headache",
                    "source": "free_text",
                }
            )
        )
        self.assertEqual(len(mirror.fields), 1)
        field = mirror.fields[0]
        self.assertEqual(field.collect_target_id, "chief_complaint")
        self.assertEqual(field.text, _KO_COMPLAINT)
        self.assertEqual(field.en_text, "I came in with a bad headache")
        self.assertEqual(field.source, "free_text")

    def test_list_columns_emit_one_field_per_item(self) -> None:
        mirror = build_clinician_mirror(
            self._state(
                character=[
                    {"text": "찌르는 듯한", "en_text": "sharp", "source": "option"},
                    {"text": "욱신거림", "en_text": "throbbing", "source": "free_text"},
                ]
            )
        )
        self.assertEqual(
            [(f.collect_target_id, f.en_text) for f in mirror.fields],
            [("character", "sharp"), ("character", "throbbing")],
        )

    def test_intake_facts_are_namespaced_by_kind(self) -> None:
        mirror = build_clinician_mirror(
            self._state(
                intake_facts=[
                    {
                        "kind": "ALLERGY",
                        "source": "PATIENT_INTAKE",
                        "display": {"text": "땅콩", "en_text": "peanut"},
                    }
                ]
            )
        )
        self.assertEqual(mirror.fields[0].collect_target_id, "intake_fact.allergy")
        self.assertEqual(mirror.fields[0].en_text, "peanut")

    def test_entries_without_text_are_skipped(self) -> None:
        mirror = build_clinician_mirror(
            self._state(
                chief_complaint={"text": "", "source": "free_text"},
                duration=None,
                character=[{"en_text": "orphan"}],
            )
        )
        self.assertEqual(mirror.fields, [])

    def test_encounter_summary_is_passed_through(self) -> None:
        mirror = build_clinician_mirror(
            self._state(encounter_summary="Patient reports headache.")
        )
        self.assertEqual(mirror.encounter_summary, "Patient reports headache.")


class TestOptionEnglishReachesState(unittest.TestCase):
    """QG's ``en_label`` must survive into ``NarrativeField.en_text``.

    The clinician dashboard is English-only, and an option pick is never sent
    through the translator — if en_label is dropped here, that answer has no
    English anywhere in the system.
    """

    def _state(self, **kwargs) -> SessionState:
        base = dict(
            session_id="s1",
            patient_id="p1",
            organization_id="o1",
            awaiting_phase="priority_questions",
            session_language="ko",
            turn_number=1,
        )
        base.update(kwargs)
        return SessionState(**base)

    def _character_question(self) -> QuestionField:
        return QuestionField(
            id="character",
            kind="multi_choice",
            prompt="어떤 느낌인가요?",
            en_prompt="What does it feel like?",
            personalization_note="t",
            collect_target_id="character",
            options=[
                QuestionOption(value="Sharp", label="찌르는 듯한", en_label="Sharp"),
                QuestionOption(value="Dull", label="둔한", en_label="Dull"),
                QuestionOption(value="Other", label="기타", en_label="Other"),
            ],
        )

    def test_option_pick_stores_en_label(self) -> None:
        updates = map_patient_answers(
            self._state(),
            {"answers": [{"question_id": "character", "value": ["Sharp", "Dull"]}]},
            [self._character_question()],
        )
        self.assertEqual(
            [(c["text"], c["en_text"]) for c in updates["character"]],
            [("찌르는 듯한", "Sharp"), ("둔한", "Dull")],
        )

    def test_free_text_other_still_translates(self) -> None:
        """The "Other" escape has no en_label — it must go through translate."""
        with patch("engine.agent_bridge.translate_to_english") as translate:
            translate.return_value = MagicMock(en_text="burning")
            updates = map_patient_answers(
                self._state(),
                {
                    "answers": [
                        {
                            "question_id": "character",
                            "value": ["Sharp", "Other: 타는 듯한"],
                        }
                    ]
                },
                [self._character_question()],
            )
        translate.assert_called_once_with("타는 듯한", "ko")
        self.assertEqual(
            [(c["text"], c["en_text"], c["source"]) for c in updates["character"]],
            [("찌르는 듯한", "Sharp", "option"), ("타는 듯한", "burning", "free_text")],
        )

    def test_missing_en_label_leaves_en_text_none(self) -> None:
        """QG non-compliance must not pass a Korean label off as English."""
        question = self._character_question()
        question.options[0].en_label = None
        updates = map_patient_answers(
            self._state(),
            {"answers": [{"question_id": "character", "value": ["Sharp"]}]},
            [question],
        )
        self.assertEqual(updates["character"][0]["text"], "찌르는 듯한")
        self.assertIsNone(updates["character"][0]["en_text"])

    def test_english_session_leaves_en_text_none(self) -> None:
        question = QuestionField(
            id="character",
            kind="multi_choice",
            prompt="What does it feel like?",
            personalization_note="t",
            collect_target_id="character",
            options=[QuestionOption(value="Sharp", label="Sharp")],
        )
        updates = map_patient_answers(
            self._state(session_language="en"),
            {"answers": [{"question_id": "character", "value": ["Sharp"]}]},
            [question],
        )
        self.assertEqual(updates["character"][0]["text"], "Sharp")
        self.assertIsNone(updates["character"][0]["en_text"])


class TestMirrorOverHttp(MockClinicalAiTestCase, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        store.reset()
        self.client = TestClient(app)

    def _start_ko_session(self) -> str:
        response = self.client.post(
            "/sessions", params={"session_language": "ko", "patient_sex": "female"}
        )
        response.raise_for_status()
        session_id = response.json()["session_id"]
        # Pre-graph: no checkpoint yet, so the mirror is empty rather than absent.
        self.assertEqual(response.json()["mirror"]["fields"], [])
        accepted = self.client.post(
            f"/sessions/{session_id}/respond", json={"answer": {"accepted": True}}
        )
        accepted.raise_for_status()
        return session_id

    def _answer_chief_complaint(self, session_id: str) -> dict:
        step = self.client.get(f"/sessions/{session_id}").json()["next_step"]
        question_id = step["questions"][0]["id"]
        response = self.client.post(
            f"/sessions/{session_id}/respond",
            json={
                "answer": {
                    "answers": [
                        {"question_id": question_id, "value": _KO_COMPLAINT}
                    ]
                }
            },
        )
        response.raise_for_status()
        return response.json()

    def test_respond_returns_english_for_korean_free_text(self) -> None:
        session_id = self._start_ko_session()
        mirror = self._answer_chief_complaint(session_id)["mirror"]

        self.assertEqual(mirror["session_language"], "ko")
        complaint = next(
            f for f in mirror["fields"] if f["collect_target_id"] == "chief_complaint"
        )
        self.assertEqual(complaint["text"], _KO_COMPLAINT)
        # The mock translator prefixes rather than translating; what matters is
        # that a non-null English companion reaches the wire at all.
        self.assertIsNotNone(complaint["en_text"])
        self.assertNotEqual(complaint["en_text"], complaint["text"])

    def test_get_session_replays_the_mirror(self) -> None:
        """Refresh recovers the clinician view — it is not browser-only state."""
        session_id = self._start_ko_session()
        from_respond = self._answer_chief_complaint(session_id)["mirror"]
        from_get = self.client.get(f"/sessions/{session_id}").json()["mirror"]
        self.assertEqual(from_get, from_respond)

    def test_english_session_needs_no_translation(self) -> None:
        response = self.client.post("/sessions", params={"session_language": "en"})
        session_id = response.json()["session_id"]
        self.client.post(
            f"/sessions/{session_id}/respond", json={"answer": {"accepted": True}}
        )
        step = self.client.get(f"/sessions/{session_id}").json()["next_step"]
        body = self.client.post(
            f"/sessions/{session_id}/respond",
            json={
                "answer": {
                    "answers": [
                        {
                            "question_id": step["questions"][0]["id"],
                            "value": "my wrist hurts",
                        }
                    ]
                }
            },
        ).json()
        complaint = next(
            f
            for f in body["mirror"]["fields"]
            if f["collect_target_id"] == "chief_complaint"
        )
        # en_text stays None for English sessions — `text` is already English,
        # so the clinician pane has nothing to render in a translation slot.
        # (`text` here is the classifier's summary, not the raw typed sentence:
        # once the classifier is ready it overwrites chief_complaint.)
        self.assertIsNone(complaint["en_text"])
        self.assertIn("my wrist hurts", complaint["text"])


class TestScaleQuestions(MockClinicalAiTestCase, unittest.TestCase):
    """Severity/impact ratings render as sliders but map like single_choice."""

    def setUp(self) -> None:
        super().setUp()
        store.reset()
        self.client = TestClient(app)

    def test_severity_is_a_scale_and_still_maps_to_the_score(self) -> None:
        response = self.client.post(
            "/sessions", params={"session_language": "en", "patient_sex": "male"}
        )
        session_id = response.json()["session_id"]
        body = self.client.post(
            f"/sessions/{session_id}/respond", json={"answer": {"accepted": True}}
        ).json()
        step = body["next_step"]
        body = self.client.post(
            f"/sessions/{session_id}/respond",
            json={
                "answer": {
                    "answers": [
                        {
                            "question_id": step["questions"][0]["id"],
                            "value": "my right wrist hurts",
                        }
                    ]
                }
            },
        ).json()

        seen_scale = False
        for _ in range(30):
            step = body["next_step"]
            if step["step_type"] == "complete":
                break
            if step["step_type"] == "body_diagram":
                answer = {
                    "region_id": "Select_RightWrist",
                    "diagram_file": step["diagram_file"],
                }
            else:
                answers = []
                for question in step.get("questions") or []:
                    if question["kind"] == "scale":
                        seen_scale = True
                        values = [o["value"] for o in question["options"] or []]
                        # The slider needs a bounded numeric range to render.
                        self.assertEqual(values, [str(i) for i in range(11)])
                    answers.append(
                        {
                            "question_id": question["id"],
                            "value": _auto_value(question),
                        }
                    )
                answer = {"answers": answers}
            body = self.client.post(
                f"/sessions/{session_id}/respond", json={"answer": answer}
            ).json()

        self.assertTrue(seen_scale, "no scale question was emitted")
        state = lifecycle.get_graph_state(session_id)
        self.assertEqual(state.severity_score, 0)


class TestTerminalStepPhase(MockClinicalAiTestCase, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        store.reset()
        self.client = TestClient(app)

    def test_complete_step_reports_phase_complete(self) -> None:
        """Regression: the terminal step reported phase="ice", so the clinician
        header kept showing "Ice" after the patient had finished."""
        response = self.client.post("/sessions", params={"session_language": "en"})
        session_id = response.json()["session_id"]

        # Walk until the graph hands back a terminal step.
        step = response.json()["next_step"]
        body = self.client.post(
            f"/sessions/{session_id}/respond", json={"answer": {"accepted": True}}
        ).json()
        for _ in range(60):
            step = body["next_step"]
            if step["step_type"] == "complete":
                break
            body = self.client.post(
                f"/sessions/{session_id}/respond",
                json={"answer": _auto_answer(step)},
            ).json()
        else:
            self.fail("never reached a complete step")

        self.assertEqual(step["step_type"], "complete")
        self.assertEqual(step["phase"], "complete")
        self.assertNotEqual(step["phase"], "ice")


def _auto_answer(step: dict) -> dict:
    """Cheapest valid answer for whatever the step is asking."""
    if step["step_type"] == "body_diagram":
        return {"region_id": "Select_RightWrist", "diagram_file": step["diagram_file"]}
    answers = []
    for question in step.get("questions") or []:
        answers.append(
            {"question_id": question["id"], "value": _auto_value(question)}
        )
    return {"answers": answers}


def _auto_value(question: dict):
    kind = question["kind"]
    if kind in ("yes_no", "consent_accept"):
        return True
    options = question.get("options") or []
    if kind == "scale":
        return options[0]["value"] if options else "0"
    if kind == "multi_choice":
        return [options[0]["value"]] if options else []
    if kind == "single_choice":
        return options[0]["value"] if options else ""
    return "my wrist hurts"


if __name__ == "__main__":
    unittest.main()
