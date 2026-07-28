import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DemoWorkspace } from "./demo-workspace";

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("DemoWorkspace onboarding", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("creates the selected-language session after identity and accepts canonical consent", async () => {
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() =>
        jsonResponse({
          session_id: "session-ko",
          status: "NOT_STARTED",
          next_step: {
            step_type: "consent",
            phase: "consent",
            turn_number: 0,
            questions: [],
          },
        }),
      )
      .mockImplementationOnce(() =>
        jsonResponse({
          status: "IN_PROGRESS",
          next_step: {
            step_type: "question_batch",
            phase: "presenting_complaint",
            turn_number: 0,
            questions: [
              {
                id: "pc_chief_complaint",
                kind: "free_text",
                prompt: "What brings you in today?",
                required: true,
                personalization_note: "deterministic",
              },
            ],
          },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<DemoWorkspace />);
    await screen.findByRole("heading", { name: "Your privacy and consent" });
    fireEvent.click(screen.getByRole("button", { name: "한국어" }));
    fireEvent.click(
      screen.getByText(
        "이번 진료를 위해 Align이 제 건강 정보를 처리하는 데 동의합니다.",
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "동의하고 계속" }));

    fireEvent.change(screen.getByLabelText("이름"), {
      target: { value: "민지" },
    });
    fireEvent.change(screen.getByLabelText("성"), {
      target: { value: "김" },
    });
    fireEvent.change(screen.getByLabelText("출생 연도"), {
      target: { value: "1992" },
    });
    fireEvent.click(screen.getByRole("button", { name: "여성" }));
    fireEvent.click(screen.getByRole("button", { name: "다음" }));

    await screen.findByText("오늘 어떤 문제로 오셨나요?");
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      "session_language=ko",
    );
    expect(String(fetchMock.mock.calls[0][0])).toContain(
      "patient_sex=female",
    );
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      answer: {
        answers: [{ question_id: "consent_privacy", value: true }],
      },
    });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  });

  it("resumes a stored tab and resynchronizes its step after a 409", async () => {
    const complaintStep = {
      step_type: "question_batch",
      phase: "presenting_complaint",
      turn_number: 1,
      questions: [
        {
          id: "pc_chief_complaint",
          kind: "free_text",
          prompt: "What brings you in today?",
          required: true,
          personalization_note: "deterministic",
        },
      ],
    };
    window.sessionStorage.setItem(
      "align-urgent-care-demo-v1",
      JSON.stringify({
        version: 1,
        stage: "clinical",
        locale: "en",
        consentAccepted: true,
        demographics: {
          givenName: "Ari",
          familyName: "Lee",
          yearOfBirth: "1990",
          patientSex: "female",
        },
        sessionId: "stored-session",
        nextStep: complaintStep,
        status: "IN_PROGRESS",
        mirrorAnswers: [],
        bodySelection: null,
      }),
    );
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() =>
        jsonResponse({
          status: "IN_PROGRESS",
          next_step: complaintStep,
        }),
      )
      .mockImplementationOnce(() =>
        jsonResponse({ detail: "stale response" }, 409),
      )
      .mockImplementationOnce(() =>
        jsonResponse({
          status: "IN_PROGRESS",
          next_step: {
            step_type: "question_batch",
            phase: "priority_questions",
            turn_number: 2,
            questions: [
              {
                id: "medication",
                kind: "yes_no",
                prompt: "Are you taking medicine for this?",
                required: true,
                personalization_note: "test",
              },
            ],
          },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<DemoWorkspace />);
    const complaint = await screen.findByRole("textbox");
    fireEvent.change(complaint, { target: { value: "Wrist pain" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit answer" }));

    expect(
      await screen.findByText("Are you taking medicine for this?"),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[2][0])).toContain(
      "/sessions/stored-session",
    );
  });
});
