import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { NextStep } from "../lib/contracts";
import {
  INITIAL_STATE,
  type DemoState,
} from "../lib/demo-state";
import { PatientPane } from "./patient-pane";

const questionsStep: NextStep = {
  step_type: "question_batch",
  phase: "priority_questions",
  turn_number: 3,
  questions: [
    {
      id: "free",
      kind: "free_text",
      prompt: "Describe it",
      required: true,
      default_value: "Existing detail",
      personalization_note: "test",
    },
    {
      id: "single",
      kind: "single_choice",
      prompt: "Pick one",
      required: true,
      options: [
        { value: "one", label: "One" },
        { value: "Other", label: "Other" },
      ],
      personalization_note: "test",
    },
    {
      id: "multi",
      kind: "multi_choice",
      prompt: "Pick many",
      required: true,
      options: [
        { value: "alpha", label: "Alpha" },
        { value: "beta", label: "Beta" },
      ],
      default_values: ["alpha"],
      personalization_note: "test",
    },
    {
      id: "yes",
      kind: "yes_no",
      prompt: "Is this new?",
      required: true,
      personalization_note: "test",
    },
    {
      id: "agree",
      kind: "consent_accept",
      prompt: "I agree",
      required: true,
      personalization_note: "test",
    },
  ],
};

function renderPane(
  state: DemoState,
  onSubmitAnswer = vi.fn(),
) {
  render(
    <PatientPane
      state={state}
      onLocale={vi.fn()}
      onConsentAccepted={vi.fn()}
      onShowIdentity={vi.fn()}
      onDemographics={vi.fn()}
      onStartEncounter={vi.fn()}
      onSubmitAnswer={onSubmitAnswer}
      onRestart={vi.fn()}
    />,
  );
  return onSubmitAnswer;
}

describe("PatientPane", () => {
  it("renders frontend-owned Korean consent", () => {
    renderPane({
      ...INITIAL_STATE,
      hydrated: true,
      restoring: false,
      locale: "ko",
    });
    expect(screen.getByRole("heading", { name: "개인정보 처리 및 동의" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "이번 진료를 위해 Align이 제 건강 정보를 처리하는 데 동의합니다.",
      ),
    ).toBeInTheDocument();
  });

  it("submits defaults, every question kind, and Other detail", () => {
    const submit = renderPane(
      {
        ...INITIAL_STATE,
        hydrated: true,
        restoring: false,
        stage: "clinical",
        nextStep: questionsStep,
        sessionId: "session-1",
        status: "IN_PROGRESS",
      },
      vi.fn(),
    );

    fireEvent.click(screen.getByRole("button", { name: "Other" }));
    fireEvent.change(screen.getByPlaceholderText("Please tell us more"), {
      target: { value: "Custom answer" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Yes" }));
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Submit answer" }));

    expect(submit).toHaveBeenCalledWith({
      answers: [
        { question_id: "free", value: "Existing detail" },
        { question_id: "single", value: "Other: Custom answer" },
        { question_id: "multi", value: ["alpha"] },
        { question_id: "yes", value: "yes" },
        { question_id: "agree", value: true },
      ],
    });
  });
});
