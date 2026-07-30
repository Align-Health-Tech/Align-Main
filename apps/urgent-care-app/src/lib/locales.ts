import type { Locale, QuestionField } from "./contracts";

export const LANGUAGE_NAMES: Record<Locale, string> = {
  en: "English",
  ko: "한국어",
  zh: "简体中文",
};

export type LocaleCopy = {
  patientPane: string;
  clinicianPane: string;
  languageLabel: string;
  consentEyebrow: string;
  consentTitle: string;
  consentIntro: string;
  consentPoints: readonly string[];
  consentCheckbox: string;
  consentContinue: string;
  identityEyebrow: string;
  identityTitle: string;
  identityIntro: string;
  givenName: string;
  familyName: string;
  yearOfBirth: string;
  patientSex: string;
  male: string;
  female: string;
  continue: string;
  questionsTitle: string;
  questionsIntro: string;
  submit: string;
  finish: string;
  skip: string;
  other: string;
  otherPlaceholder: string;
  yes: string;
  no: string;
  optional: string;
  requiredError: string;
  nameError: string;
  yearError: string;
  sexError: string;
  loading: string;
  restoring: string;
  retry: string;
  restart: string;
  restartConfirm: string;
  completeTitle: string;
  completeBody: string;
  bodyTitle: string;
  bodyHint: string;
  bodyRequired: string;
  selectedRegion: string;
  changeBodyView: string;
  genericError: string;
  staleSession: string;
};

export const COPY = {
  en: {
    patientPane: "Patient",
    clinicianPane: "Clinician",
    languageLabel: "Language",
    consentEyebrow: "Before we begin",
    consentTitle: "Your privacy and consent",
    consentIntro:
      "Align will collect your answers so the clinical team can prepare for your visit.",
    consentPoints: [
      "Your answers may include sensitive health information.",
      "The clinical team can review what you submit.",
      "This demo does not replace urgent medical care.",
    ],
    consentCheckbox:
      "I agree to Align processing my health information for this visit.",
    consentContinue: "Agree and continue",
    identityEyebrow: "About you",
    identityTitle: "Tell us who you are",
    identityIntro: "These details help the clinician identify your intake.",
    givenName: "Given name",
    familyName: "Family name",
    yearOfBirth: "Year of birth",
    patientSex: "Sex",
    male: "Male",
    female: "Female",
    continue: "Continue",
    questionsTitle: "A few questions about your health",
    questionsIntro: "Your answers update the clinician view as you go.",
    submit: "Submit answer",
    finish: "Finish",
    skip: "Skip this step",
    other: "Other",
    otherPlaceholder: "Please tell us more",
    yes: "Yes",
    no: "No",
    optional: "optional",
    requiredError: "Please answer all required questions.",
    nameError: "Enter between 1 and 80 characters.",
    yearError: "Enter a valid four-digit year of birth.",
    sexError: "Select your sex.",
    loading: "Saving your answer and preparing the next question…",
    restoring: "Restoring your visit…",
    retry: "Try again",
    restart: "Restart",
    restartConfirm: "Restart this visit? Your answers in this tab will be cleared.",
    completeTitle: "You’re all done.",
    completeBody:
      "Your answers are ready for clinician review. Keep this page open if the clinician needs the live view.",
    bodyTitle: "Where is the main problem?",
    bodyHint: "Choose one area. Orange areas are suggestions.",
    bodyRequired: "Select one area on the diagram.",
    selectedRegion: "Selected area",
    changeBodyView: "Body view",
    genericError: "Something went wrong. Please try again.",
    staleSession: "That visit is no longer available. Please start again.",
  },
  ko: {
    patientPane: "환자",
    clinicianPane: "의료진",
    languageLabel: "언어",
    consentEyebrow: "시작하기 전에",
    consentTitle: "개인정보 처리 및 동의",
    consentIntro:
      "Align은 의료진이 진료를 준비할 수 있도록 환자분의 답변을 수집합니다.",
    consentPoints: [
      "답변에는 민감한 건강 정보가 포함될 수 있습니다.",
      "제출한 내용은 의료진이 확인할 수 있습니다.",
      "이 데모는 긴급 의료 서비스를 대신하지 않습니다.",
    ],
    consentCheckbox:
      "이번 진료를 위해 Align이 제 건강 정보를 처리하는 데 동의합니다.",
    consentContinue: "동의하고 계속",
    identityEyebrow: "환자 정보",
    identityTitle: "환자분을 알려 주세요",
    identityIntro: "의료진이 문진 내용을 확인하는 데 필요한 정보입니다.",
    givenName: "이름",
    familyName: "성",
    yearOfBirth: "출생 연도",
    patientSex: "성별",
    male: "남성",
    female: "여성",
    continue: "다음",
    questionsTitle: "건강 상태에 대해 몇 가지 질문드릴게요",
    questionsIntro: "답변은 입력하는 즉시 의료진 화면에 반영됩니다.",
    submit: "답변 제출",
    finish: "완료",
    skip: "이 단계 건너뛰기",
    other: "기타",
    otherPlaceholder: "자세히 입력해 주세요",
    yes: "예",
    no: "아니요",
    optional: "선택 사항",
    requiredError: "필수 질문에 모두 답해 주세요.",
    nameError: "1자 이상 80자 이하로 입력해 주세요.",
    yearError: "올바른 네 자리 출생 연도를 입력해 주세요.",
    sexError: "성별을 선택해 주세요.",
    loading: "답변을 저장하고 다음 질문을 준비하는 중입니다…",
    restoring: "방문 정보를 복원하는 중입니다…",
    retry: "다시 시도",
    restart: "처음부터 다시",
    restartConfirm: "문진을 다시 시작할까요? 이 탭의 답변이 삭제됩니다.",
    completeTitle: "모두 완료되었습니다.",
    completeBody:
      "답변이 의료진 검토를 위해 준비되었습니다. 실시간 화면이 필요할 수 있으니 이 페이지를 열어 두세요.",
    bodyTitle: "가장 불편한 부위가 어디인가요?",
    bodyHint: "한 부위를 선택하세요. 주황색은 추천 부위입니다.",
    bodyRequired: "그림에서 한 부위를 선택해 주세요.",
    selectedRegion: "선택한 부위",
    changeBodyView: "신체 그림",
    genericError: "문제가 발생했습니다. 다시 시도해 주세요.",
    staleSession: "이 방문을 더 이상 불러올 수 없습니다. 다시 시작해 주세요.",
  },
  zh: {
    patientPane: "患者",
    clinicianPane: "医护人员",
    languageLabel: "语言",
    consentEyebrow: "开始之前",
    consentTitle: "隐私与同意",
    consentIntro: "Align 将收集您的回答，帮助医护团队为本次就诊做好准备。",
    consentPoints: [
      "您的回答可能包含敏感的健康信息。",
      "医护团队可以查看您提交的内容。",
      "本演示不能替代紧急医疗服务。",
    ],
    consentCheckbox: "我同意 Align 为本次就诊处理我的健康信息。",
    consentContinue: "同意并继续",
    identityEyebrow: "关于您",
    identityTitle: "请介绍一下自己",
    identityIntro: "这些信息有助于医护人员确认您的问诊记录。",
    givenName: "名字",
    familyName: "姓氏",
    yearOfBirth: "出生年份",
    patientSex: "生理性别",
    male: "男性",
    female: "女性",
    continue: "继续",
    questionsTitle: "请回答几个健康相关问题",
    questionsIntro: "您的回答会实时显示在医护人员视图中。",
    submit: "提交回答",
    finish: "完成",
    skip: "跳过此步骤",
    other: "其他",
    otherPlaceholder: "请补充说明",
    yes: "是",
    no: "否",
    optional: "选填",
    requiredError: "请回答所有必答问题。",
    nameError: "请输入 1 至 80 个字符。",
    yearError: "请输入有效的四位出生年份。",
    sexError: "请选择您的生理性别。",
    loading: "正在保存您的回答并准备下一个问题…",
    restoring: "正在恢复就诊信息…",
    retry: "重试",
    restart: "重新开始",
    restartConfirm: "重新开始本次问诊？此标签页中的回答将被清除。",
    completeTitle: "全部完成。",
    completeBody:
      "您的回答已准备好供医护人员查看。医护人员可能需要实时视图，请保持此页面打开。",
    bodyTitle: "主要不适部位在哪里？",
    bodyHint: "请选择一个部位。橙色区域为建议部位。",
    bodyRequired: "请在图中选择一个部位。",
    selectedRegion: "已选部位",
    changeBodyView: "身体视图",
    genericError: "出现问题，请重试。",
    staleSession: "无法继续此次就诊，请重新开始。",
  },
} satisfies Record<Locale, LocaleCopy>;

const DETERMINISTIC_PROMPTS: Partial<
  Record<QuestionField["id"], Record<Locale, string>>
> = {
  pc_chief_complaint: {
    en: "What brings you in today?",
    ko: "오늘 어떤 문제로 오셨나요?",
    zh: "您今天因为什么问题就诊？",
  },
  loc_severity: {
    en: "How severe is the pain right now? (0 = none, 10 = worst)",
    ko: "지금 통증이 얼마나 심한가요? (0 = 없음, 10 = 가장 심함)",
    zh: "目前疼痛有多严重？（0 = 无，10 = 最严重）",
  },
  nl_severity: {
    en: "How severe do you feel overall? (0–10)",
    ko: "전반적으로 증상이 얼마나 심한가요? (0–10)",
    zh: "总体感觉有多严重？（0–10）",
  },
  nl_functional: {
    en: "How much is this affecting daily activity? (0–10)",
    ko: "일상생활에 얼마나 영향을 주나요? (0–10)",
    zh: "对日常活动影响有多大？（0–10）",
  },
  survey_ease: {
    en: "How easy was this intake to complete?",
    ko: "이 문진을 작성하는 것은 얼마나 쉬웠나요?",
    zh: "完成这份问诊有多容易？",
  },
};

const SURVEY_LABELS: Record<string, Record<Locale, string>> = {
  easy: { en: "Easy", ko: "쉬웠어요", zh: "容易" },
  ok: { en: "OK", ko: "보통이었어요", zh: "一般" },
  hard: { en: "Hard", ko: "어려웠어요", zh: "困难" },
};

export function patientPrompt(question: QuestionField, locale: Locale): string {
  return DETERMINISTIC_PROMPTS[question.id]?.[locale] ?? question.prompt;
}

export function patientOptionLabel(
  question: QuestionField,
  value: string,
  fallback: string,
  locale: Locale,
): string {
  if (question.id === "survey_ease") {
    return SURVEY_LABELS[value]?.[locale] ?? fallback;
  }
  return fallback;
}

export function englishPrompt(question: QuestionField): string {
  return (
    question.en_prompt ??
    DETERMINISTIC_PROMPTS[question.id]?.en ??
    question.prompt
  );
}
