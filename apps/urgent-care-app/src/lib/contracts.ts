import type { components } from "@align/generated-types";

export type NextStep = components["schemas"]["NextStep"];
export type QuestionField = components["schemas"]["QuestionField"];
export type QuestionOption = components["schemas"]["QuestionOption"];
export type SessionResponse =
  | components["schemas"]["CreateSessionResponse"]
  | components["schemas"]["GetSessionResponse"]
  | components["schemas"]["RespondResponse"];
export type ClinicianMirror = components["schemas"]["ClinicianMirror"];
export type MirrorField = components["schemas"]["MirrorField"];

export type Locale = "en" | "ko" | "zh";
export type PatientSex = "male" | "female";
export type Pane = "patient" | "clinician";

export type Demographics = {
  givenName: string;
  familyName: string;
  yearOfBirth: string;
  patientSex: PatientSex | "";
};

export type MirrorAnswer = {
  id: string;
  phase: NextStep["phase"];
  questionId: string;
  /**
   * Which SessionState column this answer lands in — the join key against the
   * server mirror. Needed because the text does not survive: once the
   * classifier is ready it rewrites `chief_complaint` into an English summary,
   * so matching on the patient's original wording finds nothing.
   */
  collectTargetId: string | null;
  englishPrompt: string;
  nativePrompt: string;
  englishValue: string | null;
  nativeValue: string;
};

export type BodySelection = {
  diagramFile: string;
  regionId: string;
  englishLabel: string;
  nativeLabel: string;
};
