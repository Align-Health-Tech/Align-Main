"use client";

import Image from "next/image";
import { useState } from "react";
import { BodyDiagram } from "./body-diagram";
import type {
  BodySelection,
  Locale,
  NextStep,
  QuestionField,
} from "../lib/contracts";
import type { DemoState } from "../lib/demo-state";
import { validateDemographics } from "../lib/demo-state";
import {
  COPY,
  LANGUAGE_NAMES,
  patientOptionLabel,
  patientPrompt,
} from "../lib/locales";
import { englishRegionLabel, regionLabel } from "../lib/body-regions";

type Props = {
  state: DemoState;
  onLocale: (locale: Locale) => void;
  onConsentAccepted: (accepted: boolean) => void;
  onShowIdentity: () => void;
  onDemographics: (values: Partial<DemoState["demographics"]>) => void;
  onStartEncounter: () => void;
  onSubmitAnswer: (
    answer: Record<string, unknown>,
    bodySelection?: BodySelection,
  ) => void;
  onRestart: () => void;
};

export function PatientPane({
  state,
  onLocale,
  onConsentAccepted,
  onShowIdentity,
  onDemographics,
  onStartEncounter,
  onSubmitAnswer,
  onRestart,
}: Props) {
  const copy = COPY[state.locale];

  return (
    <section className="patient-pane" aria-label={copy.patientPane}>
      <header className="patient-header">
        <Image
          src="/align-logo.png"
          width={139}
          height={58}
          className="align-logo"
          alt="Align"
          priority
        />
        <button className="text-button" type="button" onClick={onRestart}>
          {copy.restart}
        </button>
      </header>
      <div className="patient-progress" aria-hidden>
        <span
          style={{
            width:
              state.stage === "consent"
                ? "18%"
                : state.stage === "identity"
                  ? "32%"
                  : state.nextStep?.step_type === "complete"
                    ? "100%"
                    : `${Math.min(92, 38 + (state.nextStep?.turn_number ?? 0) * 8)}%`,
          }}
        />
      </div>

      <div className="patient-scroll">
        {state.restoring ? (
          <CenteredStatus text={copy.restoring} />
        ) : state.stage === "consent" ? (
          <ConsentScreen
            locale={state.locale}
            accepted={state.consentAccepted}
            onLocale={onLocale}
            onAccepted={onConsentAccepted}
            onContinue={onShowIdentity}
          />
        ) : state.stage === "identity" ? (
          <IdentityScreen
            state={state}
            onChange={onDemographics}
            onContinue={onStartEncounter}
          />
        ) : state.nextStep ? (
          <ClinicalScreen
            key={`${state.nextStep.phase}:${state.nextStep.turn_number}:${state.nextStep.step_type}`}
            step={state.nextStep}
            state={state}
            onSubmit={onSubmitAnswer}
          />
        ) : (
          <CenteredStatus text={copy.loading} />
        )}
      </div>

      {state.busy ? (
        <div className="blocking-progress" role="status" aria-live="polite">
          <span className="spinner" aria-hidden />
          <strong>{copy.loading}</strong>
        </div>
      ) : null}
    </section>
  );
}

function ConsentScreen({
  locale,
  accepted,
  onLocale,
  onAccepted,
  onContinue,
}: {
  locale: Locale;
  accepted: boolean;
  onLocale: (locale: Locale) => void;
  onAccepted: (accepted: boolean) => void;
  onContinue: () => void;
}) {
  const copy = COPY[locale];
  return (
    <main className="patient-card-stack">
      <div className="language-field">
        <span>{copy.languageLabel}</span>
        <div className="language-segment" aria-label={copy.languageLabel}>
          {(Object.keys(LANGUAGE_NAMES) as Locale[]).map((language) => (
            <button
              type="button"
              key={language}
              className={language === locale ? "selected" : ""}
              onClick={() => onLocale(language)}
            >
              {LANGUAGE_NAMES[language]}
            </button>
          ))}
        </div>
      </div>
      <PageHeading
        eyebrow={copy.consentEyebrow}
        title={copy.consentTitle}
        intro={copy.consentIntro}
      />
      <article className="content-card consent-card">
        <ul className="consent-points">
          {copy.consentPoints.map((point) => (
            <li key={point}>
              <span aria-hidden>✓</span>
              {point}
            </li>
          ))}
        </ul>
        <label className={`consent-choice ${accepted ? "selected" : ""}`}>
          <input
            type="checkbox"
            checked={accepted}
            onChange={(event) => onAccepted(event.target.checked)}
          />
          <span className="checkbox-visual" aria-hidden>
            {accepted ? "✓" : ""}
          </span>
          <strong>{copy.consentCheckbox}</strong>
        </label>
      </article>
      <PrimaryButton disabled={!accepted} onClick={onContinue}>
        {copy.consentContinue}
      </PrimaryButton>
    </main>
  );
}

function IdentityScreen({
  state,
  onChange,
  onContinue,
}: {
  state: DemoState;
  onChange: (values: Partial<DemoState["demographics"]>) => void;
  onContinue: () => void;
}) {
  const [submitted, setSubmitted] = useState(false);
  const copy = COPY[state.locale];
  const errors = validateDemographics(state.demographics);

  return (
    <main className="patient-card-stack">
      <PageHeading
        eyebrow={copy.identityEyebrow}
        title={copy.identityTitle}
        intro={copy.identityIntro}
      />
      <form
        className="content-card identity-form"
        onSubmit={(event) => {
          event.preventDefault();
          setSubmitted(true);
          if (!Object.keys(errors).length) onContinue();
        }}
      >
        <TextField
          label={copy.givenName}
          value={state.demographics.givenName}
          onChange={(givenName) => onChange({ givenName })}
          error={submitted && errors.givenName ? copy.nameError : null}
          autoComplete="given-name"
        />
        <TextField
          label={copy.familyName}
          value={state.demographics.familyName}
          onChange={(familyName) => onChange({ familyName })}
          error={submitted && errors.familyName ? copy.nameError : null}
          autoComplete="family-name"
        />
        <TextField
          label={copy.yearOfBirth}
          value={state.demographics.yearOfBirth}
          onChange={(yearOfBirth) =>
            onChange({ yearOfBirth: yearOfBirth.replace(/\D/g, "").slice(0, 4) })
          }
          error={submitted && errors.yearOfBirth ? copy.yearError : null}
          inputMode="numeric"
          autoComplete="bday-year"
        />
        <fieldset className="choice-fieldset">
          <legend>{copy.patientSex}</legend>
          <div className="choice-grid two">
            {(["male", "female"] as const).map((sex) => (
              <ChoiceCard
                key={sex}
                selected={state.demographics.patientSex === sex}
                onClick={() => onChange({ patientSex: sex })}
                label={sex === "male" ? copy.male : copy.female}
              />
            ))}
          </div>
          {submitted && errors.patientSex ? (
            <p className="field-error">{copy.sexError}</p>
          ) : null}
        </fieldset>
        {state.error ? <InlineError message={state.error} /> : null}
        <PrimaryButton type="submit" disabled={state.busy}>
          {copy.continue}
        </PrimaryButton>
      </form>
    </main>
  );
}

function ClinicalScreen({
  step,
  state,
  onSubmit,
}: {
  step: NextStep;
  state: DemoState;
  onSubmit: Props["onSubmitAnswer"];
}) {
  const copy = COPY[state.locale];
  if (step.step_type === "complete") {
    return (
      <main className="patient-card-stack completion-screen">
        <div className="completion-icon" aria-hidden>
          ✓
        </div>
        <PageHeading title={copy.completeTitle} intro={copy.completeBody} />
        {state.error ? <InlineError message={state.error} /> : null}
      </main>
    );
  }
  if (step.step_type === "body_diagram") {
    return (
      <BodyDiagramForm
        step={step}
        state={state}
        onSubmit={onSubmit}
      />
    );
  }
  return <QuestionForm step={step} state={state} onSubmit={onSubmit} />;
}

function QuestionForm({
  step,
  state,
  onSubmit,
}: {
  step: NextStep;
  state: DemoState;
  onSubmit: Props["onSubmitAnswer"];
}) {
  const copy = COPY[state.locale];
  const [values, setValues] = useState<Record<string, unknown>>(() =>
    defaultsForQuestions(step.questions ?? []),
  );
  const [otherValues, setOtherValues] = useState<Record<string, string>>({});
  const [validationError, setValidationError] = useState(false);
  const questions = step.questions ?? [];
  const skippable =
    step.phase === "optional_questions" ||
    (questions.length > 0 && questions.every((question) => !question.required));

  const submit = () => {
    const missing = questions.some(
      (question) =>
        question.required && !hasQuestionValue(question, values[question.id]),
    );
    const missingOther = questions.some((question) => {
      const value = values[question.id];
      const includesOther = Array.isArray(value)
        ? value.includes("Other")
        : value === "Other";
      return includesOther && !otherValues[question.id]?.trim();
    });
    if (missing || missingOther) {
      setValidationError(true);
      return;
    }
    const answers = questions.flatMap((question) => {
      const value = values[question.id];
      if (!hasQuestionValue(question, value)) return [];
      return [
        {
          question_id: question.id,
          value: withOtherDetail(value, otherValues[question.id]),
        },
      ];
    });
    onSubmit({ answers });
  };

  return (
    <main className="patient-card-stack">
      <PageHeading
        title={copy.questionsTitle}
        intro={copy.questionsIntro}
      />
      <div className="question-stack">
        {questions.map((question) => (
          <QuestionControl
            key={question.id}
            question={question}
            locale={state.locale}
            value={values[question.id]}
            otherValue={otherValues[question.id] ?? ""}
            onChange={(value) =>
              setValues((current) => ({ ...current, [question.id]: value }))
            }
            onOtherChange={(value) =>
              setOtherValues((current) => ({
                ...current,
                [question.id]: value,
              }))
            }
          />
        ))}
      </div>
      {validationError ? <InlineError message={copy.requiredError} /> : null}
      {state.error ? <InlineError message={state.error} /> : null}
      <div className="action-stack">
        <PrimaryButton onClick={submit} disabled={state.busy}>
          {step.step_type === "survey" ? copy.finish : copy.submit}
        </PrimaryButton>
        {skippable ? (
          <button
            type="button"
            className="secondary-button"
            disabled={state.busy}
            onClick={() => onSubmit({ skip: true })}
          >
            {copy.skip}
          </button>
        ) : null}
      </div>
    </main>
  );
}

function QuestionControl({
  question,
  locale,
  value,
  otherValue,
  onChange,
  onOtherChange,
}: {
  question: QuestionField;
  locale: Locale;
  value: unknown;
  otherValue: string;
  onChange: (value: unknown) => void;
  onOtherChange: (value: string) => void;
}) {
  const copy = COPY[locale];
  const options =
    question.kind === "yes_no"
      ? [
          { value: "yes", label: copy.yes },
          { value: "no", label: copy.no },
        ]
      : (question.options ?? []).map((option) => ({
          value: option.value,
          label: patientOptionLabel(
            question,
            option.value,
            option.label,
            locale,
          ),
        }));
  const showOther = Array.isArray(value)
    ? value.includes("Other")
    : value === "Other";

  return (
    <fieldset className="content-card question-card">
      <legend>
        {patientPrompt(question, locale)}
        {!question.required ? (
          <span className="optional"> · {copy.optional}</span>
        ) : null}
      </legend>
      {question.kind === "free_text" ? (
        <textarea
          className="text-field text-area"
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onChange(event.target.value)}
          rows={4}
        />
      ) : question.kind === "scale" ? (
        <ScaleField
          question={question}
          locale={locale}
          value={value}
          onChange={onChange}
        />
      ) : question.kind === "consent_accept" ? (
        <label className={`consent-choice ${value === true ? "selected" : ""}`}>
          <input
            type="checkbox"
            checked={value === true}
            onChange={(event) => onChange(event.target.checked)}
          />
          <span className="checkbox-visual" aria-hidden>
            {value === true ? "✓" : ""}
          </span>
          <strong>{patientPrompt(question, locale)}</strong>
        </label>
      ) : (
        <div className="choice-grid">
          {options.map((option) => {
            const selected = Array.isArray(value)
              ? value.includes(option.value)
              : value === option.value;
            return (
              <ChoiceCard
                key={option.value}
                selected={selected}
                label={option.label}
                onClick={() => {
                  if (question.kind === "multi_choice") {
                    const current = Array.isArray(value) ? value : [];
                    onChange(
                      selected
                        ? current.filter((item) => item !== option.value)
                        : [...current, option.value],
                    );
                  } else {
                    onChange(option.value);
                  }
                }}
              />
            );
          })}
        </div>
      )}
      {showOther ? (
        <input
          className="text-field other-field"
          value={otherValue}
          placeholder={copy.otherPlaceholder}
          onChange={(event) => onOtherChange(event.target.value)}
          autoFocus
        />
      ) : null}
    </fieldset>
  );
}

/**
 * 0–N rating slider.
 *
 * Deliberately starts unanswered rather than defaulting to a midpoint — an
 * untouched slider must not submit a severity the patient never chose. The
 * readout stays "—" until they interact, and `hasQuestionValue` keeps the batch
 * invalid until then.
 */
function ScaleField({
  question,
  locale,
  value,
  onChange,
}: {
  question: QuestionField;
  locale: Locale;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const copy = COPY[locale];
  const points = (question.options ?? [])
    .map((option) => Number(option.value))
    .filter((point) => Number.isFinite(point));
  const min = points.length ? Math.min(...points) : 0;
  const max = points.length ? Math.max(...points) : 10;

  const answered = value !== null && value !== undefined && value !== "";
  const current = answered ? Number(value) : min;

  // Committing on pointer down as well as on change is load-bearing: a patient
  // whose answer equals the resting position (min) would otherwise never fire a
  // change event, leaving the question permanently unanswerable.
  const commit = (next: number) => onChange(String(next));

  return (
    <div className="scale-field">
      <output className={answered ? "scale-readout" : "scale-readout empty"}>
        {answered ? current : "—"}
      </output>
      <input
        type="range"
        className="scale-slider"
        min={min}
        max={max}
        step={1}
        value={current}
        aria-valuetext={answered ? String(current) : copy.scaleUnanswered}
        onPointerDown={() => commit(current)}
        onChange={(event) => commit(Number(event.target.value))}
      />
      <div className="scale-ends" aria-hidden>
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

function BodyDiagramForm({
  step,
  state,
  onSubmit,
}: {
  step: NextStep;
  state: DemoState;
  onSubmit: Props["onSubmitAnswer"];
}) {
  const copy = COPY[state.locale];
  const [selected, setSelected] = useState("");
  const [diagramFile, setDiagramFile] = useState(step.diagram_file ?? "");
  const [showError, setShowError] = useState(false);

  return (
    <main className="patient-card-stack">
      <PageHeading title={copy.bodyTitle} intro={copy.bodyHint} />
      <article className="content-card">
        <BodyDiagram
          diagramFile={step.diagram_file}
          highlightedRegionIds={step.highlighted_region_ids}
          locale={state.locale}
          patientSex={state.demographics.patientSex}
          selected={selected}
          onSelected={(regionId, file) => {
            setSelected(regionId);
            setDiagramFile(file);
            setShowError(false);
          }}
        />
      </article>
      {showError ? <InlineError message={copy.bodyRequired} /> : null}
      {state.error ? <InlineError message={state.error} /> : null}
      <PrimaryButton
        onClick={() => {
          if (!selected || !diagramFile) {
            setShowError(true);
            return;
          }
          onSubmit(
            { region_id: selected },
            {
              diagramFile,
              regionId: selected,
              englishLabel: englishRegionLabel(selected),
              nativeLabel: regionLabel(selected, state.locale),
            },
          );
        }}
      >
        {copy.submit}
      </PrimaryButton>
    </main>
  );
}

function PageHeading({
  eyebrow,
  title,
  intro,
}: {
  eyebrow?: string;
  title: string;
  intro?: string;
}) {
  return (
    <div className="page-heading">
      {eyebrow ? <span>{eyebrow}</span> : null}
      <h1>{title}</h1>
      {intro ? <p>{intro}</p> : null}
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
  error,
  ...inputProps
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error: string | null;
} & Pick<
  React.InputHTMLAttributes<HTMLInputElement>,
  "autoComplete" | "inputMode"
>) {
  return (
    <label className="text-field-label">
      <span>{label}</span>
      <input
        className="text-field"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        {...inputProps}
      />
      {error ? <small className="field-error">{error}</small> : null}
    </label>
  );
}

function ChoiceCard({
  selected,
  onClick,
  label,
}: {
  selected: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className={`choice-card ${selected ? "selected" : ""}`}
      aria-pressed={selected}
      onClick={onClick}
    >
      <span className="choice-indicator">{selected ? "✓" : ""}</span>
      <span>{label}</span>
    </button>
  );
}

function PrimaryButton({
  children,
  type = "button",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className="primary-button" type={type} {...props}>
      {children}
    </button>
  );
}

function InlineError({ message }: { message: string }) {
  return (
    <p className="inline-error" role="alert">
      {message}
    </p>
  );
}

function CenteredStatus({ text }: { text: string }) {
  return (
    <div className="centered-status" role="status">
      <span className="spinner" aria-hidden />
      <p>{text}</p>
    </div>
  );
}

function defaultsForQuestions(
  questions: QuestionField[],
): Record<string, unknown> {
  return Object.fromEntries(
    questions.map((question) => [
      question.id,
      question.default_values ??
        question.default_value ??
        (question.kind === "multi_choice" ? [] : ""),
    ]),
  );
}

function hasQuestionValue(question: QuestionField, value: unknown): boolean {
  if (question.kind === "consent_accept") return value === true;
  if (Array.isArray(value)) return value.length > 0;
  return value !== null && value !== undefined && String(value).trim() !== "";
}

function withOtherDetail(value: unknown, detail?: string): unknown {
  if (Array.isArray(value)) {
    return value.map((item) =>
      item === "Other" ? `Other: ${detail?.trim() ?? ""}` : item,
    );
  }
  return value === "Other" ? `Other: ${detail?.trim() ?? ""}` : value;
}
