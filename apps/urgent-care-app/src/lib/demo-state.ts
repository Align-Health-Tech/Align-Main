import type {
  BodySelection,
  Demographics,
  Locale,
  MirrorAnswer,
  NextStep,
  Pane,
  QuestionField,
} from "./contracts";
import {
  COPY,
  englishPrompt,
  patientOptionLabel,
  patientPrompt,
} from "./locales";

export type DemoStage = "consent" | "identity" | "clinical";

export type DemoState = {
  hydrated: boolean;
  restoring: boolean;
  stage: DemoStage;
  locale: Locale;
  consentAccepted: boolean;
  demographics: Demographics;
  sessionId: string | null;
  nextStep: NextStep | null;
  status: string | null;
  mirrorAnswers: MirrorAnswer[];
  bodySelection: BodySelection | null;
  activePane: Pane;
  busy: boolean;
  error: string | null;
};

export type DemoAction =
  | { type: "HYDRATE"; state: Partial<DemoState> | null }
  | { type: "SET_LOCALE"; locale: Locale }
  | { type: "ACCEPT_CONSENT"; accepted: boolean }
  | { type: "SHOW_IDENTITY" }
  | { type: "UPDATE_DEMOGRAPHICS"; values: Partial<Demographics> }
  | {
      type: "SESSION_CREATED";
      sessionId: string;
      nextStep: NextStep;
      status: string;
    }
  | { type: "SYNC_SESSION"; nextStep: NextStep; status: string }
  | {
      type: "ANSWER_SAVED";
      nextStep: NextStep;
      status: string;
      mirrorAnswers: MirrorAnswer[];
      bodySelection?: BodySelection;
    }
  | { type: "SET_BUSY"; busy: boolean }
  | { type: "SET_ERROR"; error: string | null }
  | { type: "SET_PANE"; pane: Pane }
  | { type: "MARK_COMPLETED"; status: string }
  | { type: "RESET" };

const EMPTY_DEMOGRAPHICS: Demographics = {
  givenName: "",
  familyName: "",
  yearOfBirth: "",
  patientSex: "",
};

export const INITIAL_STATE: DemoState = {
  hydrated: false,
  restoring: true,
  stage: "consent",
  locale: "en",
  consentAccepted: false,
  demographics: EMPTY_DEMOGRAPHICS,
  sessionId: null,
  nextStep: null,
  status: null,
  mirrorAnswers: [],
  bodySelection: null,
  activePane: "patient",
  busy: false,
  error: null,
};

export function demoReducer(
  state: DemoState,
  action: DemoAction,
): DemoState {
  switch (action.type) {
    case "HYDRATE":
      return {
        ...INITIAL_STATE,
        ...action.state,
        demographics: {
          ...EMPTY_DEMOGRAPHICS,
          ...action.state?.demographics,
        },
        hydrated: true,
        restoring: false,
        busy: false,
        error: null,
      };
    case "SET_LOCALE":
      if (state.sessionId) return state;
      return { ...state, locale: action.locale, error: null };
    case "ACCEPT_CONSENT":
      return { ...state, consentAccepted: action.accepted, error: null };
    case "SHOW_IDENTITY":
      return state.consentAccepted
        ? { ...state, stage: "identity", error: null }
        : { ...state, error: COPY[state.locale].requiredError };
    case "UPDATE_DEMOGRAPHICS":
      return {
        ...state,
        demographics: { ...state.demographics, ...action.values },
        error: null,
      };
    case "SESSION_CREATED":
      return {
        ...state,
        sessionId: action.sessionId,
        nextStep: action.nextStep,
        status: action.status,
        error: null,
      };
    case "SYNC_SESSION":
      return {
        ...state,
        stage: "clinical",
        nextStep: action.nextStep,
        status: action.status,
        restoring: false,
        busy: false,
        error: null,
      };
    case "ANSWER_SAVED":
      return {
        ...state,
        stage: "clinical",
        nextStep: action.nextStep,
        status: action.status,
        mirrorAnswers: [
          ...state.mirrorAnswers,
          ...action.mirrorAnswers,
        ],
        bodySelection: action.bodySelection ?? state.bodySelection,
        busy: false,
        error: null,
      };
    case "SET_BUSY":
      return { ...state, busy: action.busy, error: null };
    case "SET_ERROR":
      return { ...state, busy: false, restoring: false, error: action.error };
    case "SET_PANE":
      return { ...state, activePane: action.pane };
    case "MARK_COMPLETED":
      return { ...state, status: action.status, busy: false, error: null };
    case "RESET":
      return {
        ...INITIAL_STATE,
        hydrated: true,
        restoring: false,
        locale: state.locale,
      };
  }
}

const STORAGE_KEY = "align-urgent-care-demo-v1";
const STORAGE_VERSION = 1;

type StoredDemoState = {
  version: number;
  stage: DemoStage;
  locale: Locale;
  consentAccepted: boolean;
  demographics: Demographics;
  sessionId: string | null;
  nextStep: NextStep | null;
  status: string | null;
  mirrorAnswers: MirrorAnswer[];
  bodySelection: BodySelection | null;
};

export function loadStoredState(): Partial<DemoState> | null {
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as StoredDemoState;
    if (
      parsed.version !== STORAGE_VERSION ||
      !["en", "ko", "zh"].includes(parsed.locale)
    ) {
      window.sessionStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    window.sessionStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function saveStoredState(state: DemoState): void {
  if (!state.hydrated) return;
  const stored: StoredDemoState = {
    version: STORAGE_VERSION,
    stage: state.stage,
    locale: state.locale,
    consentAccepted: state.consentAccepted,
    demographics: state.demographics,
    sessionId: state.sessionId,
    nextStep: state.nextStep,
    status: state.status,
    mirrorAnswers: state.mirrorAnswers,
    bodySelection: state.bodySelection,
  };
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
}

export function clearStoredState(): void {
  window.sessionStorage.removeItem(STORAGE_KEY);
}

export function validateDemographics(
  demographics: Demographics,
): Partial<Record<keyof Demographics, string>> {
  const errors: Partial<Record<keyof Demographics, string>> = {};
  if (
    demographics.givenName.trim().length < 1 ||
    demographics.givenName.trim().length > 80
  ) {
    errors.givenName = "invalid";
  }
  if (
    demographics.familyName.trim().length < 1 ||
    demographics.familyName.trim().length > 80
  ) {
    errors.familyName = "invalid";
  }
  const year = Number(demographics.yearOfBirth);
  const currentYear = new Date().getFullYear();
  if (
    !/^\d{4}$/.test(demographics.yearOfBirth) ||
    year < currentYear - 120 ||
    year > currentYear
  ) {
    errors.yearOfBirth = "invalid";
  }
  if (!demographics.patientSex) {
    errors.patientSex = "invalid";
  }
  return errors;
}

export function buildMirrorAnswers(
  step: NextStep,
  answer: Record<string, unknown>,
  locale: Locale,
): MirrorAnswer[] {
  const rows = Array.isArray(answer.answers) ? answer.answers : [];
  return rows.flatMap((raw, index) => {
    if (!raw || typeof raw !== "object") return [];
    const questionId =
      "question_id" in raw && typeof raw.question_id === "string"
        ? raw.question_id
        : null;
    if (!questionId) return [];
    const question = step.questions?.find((item) => item.id === questionId);
    if (!question || !("value" in raw)) return [];
    const rawValue: unknown = raw.value;
    const values: unknown[] = Array.isArray(rawValue) ? rawValue : [rawValue];
    const displayed: { native: string; english: string | null }[] = values
      .map((value) => displayAnswer(question, value, locale))
      .filter((value): value is { native: string; english: string | null } =>
        Boolean(value),
      );
    if (!displayed.length) return [];
    return [
      {
        id: `${step.phase}:${step.turn_number}:${question.id}:${index}`,
        phase: step.phase,
        questionId: question.id,
        englishPrompt: englishPrompt(question),
        nativePrompt: patientPrompt(question, locale),
        englishValue: displayed.every((value) => value.english !== null)
          ? displayed.map((value) => value.english).join(", ")
          : null,
        nativeValue: displayed.map((value) => value.native).join(", "),
      },
    ];
  });
}

function displayAnswer(
  question: QuestionField,
  rawValue: unknown,
  locale: Locale,
): { native: string; english: string | null } | null {
  if (rawValue === null || rawValue === undefined || rawValue === "") {
    return null;
  }
  if (typeof rawValue === "boolean") {
    return {
      native: rawValue ? COPY[locale].yes : COPY[locale].no,
      english: rawValue ? "Yes" : "No",
    };
  }
  const value = String(rawValue);
  if (value.startsWith("Other:")) {
    const detail = value.slice("Other:".length).trim();
    return {
      native: `${COPY[locale].other}: ${detail}`,
      english: locale === "en" ? `Other: ${detail}` : null,
    };
  }
  if (question.kind === "yes_no") {
    const yes = ["yes", "true"].includes(value.toLowerCase());
    return {
      native: yes ? COPY[locale].yes : COPY[locale].no,
      english: yes ? "Yes" : "No",
    };
  }
  const option = question.options?.find((item) => item.value === value);
  if (option) {
    return {
      native: patientOptionLabel(question, value, option.label, locale),
      english: option.en_label ?? option.label,
    };
  }
  return { native: value, english: locale === "en" ? value : null };
}
