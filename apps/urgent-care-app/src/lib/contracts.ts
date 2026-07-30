import type { components } from "@align/generated-types";

export type NextStep = components["schemas"]["NextStep"];
export type QuestionField = components["schemas"]["QuestionField"];
export type QuestionOption = components["schemas"]["QuestionOption"];
export type SessionResponse =
  | components["schemas"]["CreateSessionResponse"]
  | components["schemas"]["GetSessionResponse"]
  | components["schemas"]["RespondResponse"];

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
