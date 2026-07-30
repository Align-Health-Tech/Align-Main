import { describe, expect, it } from "vitest";
import type { NextStep } from "./contracts";
import {
  INITIAL_STATE,
  buildMirrorAnswers,
  demoReducer,
  validateDemographics,
} from "./demo-state";

const koreanStep: NextStep = {
  step_type: "question_batch",
  phase: "presenting_complaint",
  turn_number: 1,
  questions: [
    {
      id: "pc_chief_complaint",
      kind: "free_text",
      prompt: "오늘 어떤 문제로 오셨나요?",
      en_prompt: "What brings you in today?",
      required: true,
      personalization_note: "test",
      collect_target_id: "chief_complaint",
    },
    {
      id: "duration",
      kind: "single_choice",
      prompt: "언제부터였나요?",
      en_prompt: "How long have you had this?",
      required: true,
      personalization_note: "test",
      options: [
        {
          value: "week",
          label: "일주일 이내",
          en_label: "Within a week",
        },
      ],
    },
  ],
};

describe("demo reducer", () => {
  it("allows language changes before session creation and locks afterwards", () => {
    const korean = demoReducer(INITIAL_STATE, {
      type: "SET_LOCALE",
      locale: "ko",
    });
    expect(korean.locale).toBe("ko");
    const started = { ...korean, sessionId: "session-1" };
    expect(
      demoReducer(started, { type: "SET_LOCALE", locale: "zh" }).locale,
    ).toBe("ko");
  });

  it("validates required identity fields and current year bounds", () => {
    expect(
      validateDemographics({
        givenName: "",
        familyName: "Li",
        yearOfBirth: "1800",
        patientSex: "",
      }),
    ).toEqual({
      givenName: "invalid",
      yearOfBirth: "invalid",
      patientSex: "invalid",
    });
    expect(
      validateDemographics({
        givenName: "Mei",
        familyName: "Li",
        yearOfBirth: "1990",
        patientSex: "female",
      }),
    ).toEqual({});
  });

  it("uses English companions while retaining Korean patient wording", () => {
    const rows = buildMirrorAnswers(
      koreanStep,
      {
        answers: [
          { question_id: "pc_chief_complaint", value: "손목이 아파요" },
          { question_id: "duration", value: "week" },
        ],
      },
      "ko",
    );
    expect(rows[0]).toMatchObject({
      englishPrompt: "What brings you in today?",
      englishValue: null,
      nativeValue: "손목이 아파요",
    });
    expect(rows[1]).toMatchObject({
      englishPrompt: "How long have you had this?",
      englishValue: "Within a week",
      nativeValue: "일주일 이내",
    });
  });
});
