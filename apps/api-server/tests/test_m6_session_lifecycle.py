"""M6: HTTP status machine consent → graph → survey → AWAITING_REVIEW → COMPLETED."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.session_store import store
from tests.mock_clinical_ai import MockClinicalAiTestCase

_TRANSCRIPT_DIR = Path(__file__).resolve().parent / "transcripts"


class TestM6SessionLifecycle(MockClinicalAiTestCase, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        store.reset()
        self.client = TestClient(app)
        self._log: list[str] = []

    def _line(self, text: str) -> None:
        self._log.append(text)

    def _write_transcript(self) -> Path:
        _TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        path = _TRANSCRIPT_DIR / f"m6_walk_{stamp}.txt"
        path.write_text("\n".join(self._log) + "\n", encoding="utf-8")
        return path

    def _dump_step(self, label: str, payload: dict, answer: dict | None = None) -> None:
        step = payload["next_step"]
        status = payload["status"]
        self._line(f"## {label}")
        self._line(f"status: {status}")
        self._line(f"step_type: {step['step_type']}  phase: {step['phase']}  turn: {step['turn_number']}")
        if step.get("questions"):
            for q in step["questions"]:
                self._line(f"  ask [{q['id']}] ({q['kind']}): {q['prompt']}")
        if step.get("diagram_file"):
            self._line(f"  body_diagram: {step['diagram_file']} highlights={step.get('highlighted_region_ids')}")
        if answer is not None:
            self._line(f"  answer → {answer}")
        self._line("")

    def test_full_walk_consent_to_completed(self) -> None:
        transitions: list[str] = []

        # 1. Create → consent
        r = self.client.post("/sessions")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        sid = data["session_id"]
        self.assertEqual(data["status"], "NOT_STARTED")
        self.assertEqual(data["next_step"]["phase"], "consent")
        transitions.append(data["status"])
        self._dump_step("POST /sessions", data)

        # 2. Consent accept → IN_PROGRESS + PC
        consent_answer = {
            "answers": [{"question_id": "consent_privacy", "value": True}]
        }
        r = self.client.post(f"/sessions/{sid}/respond", json={"answer": consent_answer})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "IN_PROGRESS")
        self.assertEqual(data["next_step"]["phase"], "presenting_complaint")
        transitions.append(data["status"])
        self._dump_step("consent accept", data, consent_answer)

        # 3. PC free text → localised detail (body diagram)
        pc = {
            "answers": [
                {
                    "question_id": "pc_chief_complaint",
                    "value": "pain in my right wrist",
                }
            ]
        }
        r = self.client.post(f"/sessions/{sid}/respond", json={"answer": pc})
        data = r.json()
        self.assertEqual(data["next_step"]["step_type"], "body_diagram")
        self._dump_step("presenting_complaint", data, pc)

        # 4. Body diagram + severity/onset → priority
        diagram = {"region_id": "Select_RightWrist"}
        r = self.client.post(f"/sessions/{sid}/respond", json={"answer": diagram})
        data = r.json()
        self.assertEqual(data["next_step"]["phase"], "localised_detail")
        self._dump_step("body_diagram", data, diagram)

        loc = {
            "answers": [
                {"question_id": "loc_severity", "value": "7"},
                {"question_id": "duration", "value": "Within a week"},
            ]
        }
        r = self.client.post(f"/sessions/{sid}/respond", json={"answer": loc})
        data = r.json()
        self.assertEqual(data["next_step"]["phase"], "priority_questions")
        self._dump_step("localised_detail questions", data, loc)

        # 5. Priority → redflag
        priority = {"answers": [{"question_id": "meds_q1", "value": "no"}]}
        r = self.client.post(f"/sessions/{sid}/respond", json={"answer": priority})
        data = r.json()
        self.assertEqual(data["next_step"]["phase"], "redflag_screening")
        self._dump_step("priority_questions", data, priority)

        # 6. Redflag no → optional
        redflag = {
            "answers": [
                {"question_id": "rf_chest_pain", "value": "no"},
                {"question_id": "rf_neuro", "value": "no"},
            ]
        }
        r = self.client.post(f"/sessions/{sid}/respond", json={"answer": redflag})
        data = r.json()
        self.assertEqual(data["next_step"]["phase"], "optional_questions")
        self._dump_step("redflag_screening", data, redflag)

        # 7. Optional skip → ice
        skip = {"skip": True}
        r = self.client.post(f"/sessions/{sid}/respond", json={"answer": skip})
        data = r.json()
        self.assertEqual(data["next_step"]["phase"], "ice")
        self.assertEqual(data["status"], "IN_PROGRESS")
        self._dump_step("optional skip", data, skip)

        # 8. ICE → silent review → survey (still IN_PROGRESS)
        ice = {
            "answers": [
                {"question_id": "ice_idea", "value": "Maybe a sprain"},
                {
                    "question_id": "ice_concern",
                    "value": "Worried about a fracture",
                },
                {"question_id": "ice_expectation", "value": "Want an X-ray"},
            ]
        }
        r = self.client.post(f"/sessions/{sid}/respond", json={"answer": ice})
        data = r.json()
        self.assertEqual(data["status"], "IN_PROGRESS", "survey must not use AWAITING_REVIEW")
        self.assertEqual(data["next_step"]["phase"], "survey")
        self.assertEqual(data["next_step"]["step_type"], "survey")
        self.assertEqual(self.ai.fake_nurse_call_count, 1)
        self._dump_step("ice → survey (graph complete intercepted)", data, ice)

        # 9. Survey → AWAITING_REVIEW + patient complete
        survey = {
            "answers": [{"question_id": "survey_ease", "value": "easy"}]
        }
        r = self.client.post(f"/sessions/{sid}/respond", json={"answer": survey})
        data = r.json()
        self.assertEqual(data["status"], "AWAITING_REVIEW")
        self.assertEqual(data["next_step"]["step_type"], "complete")
        transitions.append(data["status"])
        self._dump_step("survey answer", data, survey)

        # 10. Clinician mark complete
        r = self.client.post(f"/clinician/sessions/{sid}/complete")
        self.assertEqual(r.status_code, 200)
        done = r.json()
        self.assertEqual(done["status"], "COMPLETED")
        transitions.append(done["status"])
        self._line("## clinician mark complete")
        self._line(f"status: {done['status']}")
        self._line("")

        self._line("## status transitions")
        self._line(" → ".join(transitions))
        self.assertEqual(
            transitions,
            ["NOT_STARTED", "IN_PROGRESS", "AWAITING_REVIEW", "COMPLETED"],
        )

        path = self._write_transcript()
        print(f"M6 transcript: {path}")

    def test_clinician_complete_requires_awaiting_review(self) -> None:
        r = self.client.post("/sessions")
        sid = r.json()["session_id"]
        r = self.client.post(f"/clinician/sessions/{sid}/complete")
        self.assertEqual(r.status_code, 409)

    def test_consent_required_before_graph(self) -> None:
        r = self.client.post("/sessions")
        sid = r.json()["session_id"]
        r = self.client.post(
            f"/sessions/{sid}/respond",
            json={
                "answer": {
                    "answers": [
                        {
                            "question_id": "pc_chief_complaint",
                            "value": "wrist pain",
                        }
                    ]
                }
            },
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(store.get_session(sid).status, "NOT_STARTED")


if __name__ == "__main__":
    unittest.main()
