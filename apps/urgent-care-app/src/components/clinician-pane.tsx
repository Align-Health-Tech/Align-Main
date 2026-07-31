"use client";

import Image from "next/image";
import { useState, type ReactNode } from "react";
import type { DemoState } from "../lib/demo-state";
import type { MirrorAnswer } from "../lib/contracts";
import { LANGUAGE_NAMES_EN } from "../lib/locales";
import { ReadOnlyBodyDiagram } from "./body-diagram";

type Props = {
  state: DemoState;
  onComplete: () => void;
};

export function ClinicianPane({ state, onComplete }: Props) {
  const demographics = state.demographics;
  const chiefComplaint = state.mirrorAnswers.find(
    (row) => row.questionId === "pc_chief_complaint",
  );
  const redFlags = state.mirrorAnswers.filter(
    (row) => row.phase === "redflag_screening",
  );
  const ice = state.mirrorAnswers.filter((row) => row.phase === "ice");
  const liveFields = state.mirrorAnswers.filter(
    (row) =>
      row !== chiefComplaint &&
      row.phase !== "redflag_screening" &&
      row.phase !== "ice" &&
      row.phase !== "survey",
  );
  const fullName =
    [demographics.givenName, demographics.familyName]
      .filter(Boolean)
      .join(" ") || "Not collected yet";
  const age = ageFromYear(demographics.yearOfBirth);

  return (
    <section className="clinician-pane" aria-label="Clinician">
      <header className="clinician-header">
        <div>
          <span className="clinician-kicker">LIVE ENCOUNTER</span>
          <h1>Clinician view</h1>
        </div>
        <Image
          src="/align-logo.png"
          width={111}
          height={46}
          className="clinician-logo"
          alt="Align"
        />
      </header>

      <div className="clinician-scroll">
        <div className="status-strip">
          <span className={`status-dot ${statusTone(state.status)}`} />
          <div>
            <small>Current phase</small>
            <strong>{formatPhase(state.nextStep?.phase)}</strong>
          </div>
          <span className="status-pill">{formatStatus(state.status)}</span>
        </div>

        <ClinicianCard
          title="Patient bio"
          tone="cream"
          copyText={[
            fullName,
            demographics.patientSex || "Not collected yet",
            age === null ? "Not collected yet" : `${age} years`,
            LANGUAGE_NAMES_EN[state.locale],
          ].join("\n")}
        >
          <h2 className="patient-name">{fullName}</h2>
          <div className="bio-grid">
            <BioItem
              label="Sex"
              value={capitalize(demographics.patientSex) || "Not collected yet"}
            />
            <BioItem
              label="Age"
              value={age === null ? "Not collected yet" : String(age)}
            />
            <BioItem
              label="Preferred language"
              value={LANGUAGE_NAMES_EN[state.locale]}
              wide
            />
          </div>
        </ClinicianCard>

        <ClinicianCard
          title="Chief complaint"
          subtitle="Patient’s main reason for attending"
          tone="lavender"
          copyText={mirrorCopy(chiefComplaint)}
        >
          {chiefComplaint ? (
            <TranslatedAnswer answer={chiefComplaint} prominent />
          ) : (
            <Placeholder />
          )}
        </ClinicianCard>

        <CollapsibleCard
          title="Live clinical fields"
          copyText={liveFields.map(mirrorCopy).join("\n\n")}
        >
          <AnswerList answers={liveFields} />
        </CollapsibleCard>

        <ClinicianCard
          title="Body site"
          subtitle="Same body view used by the patient"
          tone="lavender"
          copyText={
            state.bodySelection
              ? state.bodySelection.englishLabel
              : "Not collected yet"
          }
        >
          {state.bodySelection ? (
            <>
              <ReadOnlyBodyDiagram
                file={state.bodySelection.diagramFile}
                regionId={state.bodySelection.regionId}
              />
              <div className="body-label-row">
                <span className="legend-swatch" />
                <strong>{state.bodySelection.englishLabel}</strong>
              </div>
            </>
          ) : (
            <Placeholder />
          )}
        </ClinicianCard>

        <ClinicianCard
          title="Red flags"
          subtitle="Raised answers require clinical review"
          tone={redFlags.some(isAffirmative) ? "red" : "lavender"}
          copyText={redFlags.map(mirrorCopy).join("\n\n")}
        >
          <AnswerList answers={redFlags} redFlags />
        </ClinicianCard>

        <CollapsibleCard
          title="Ideas, concerns & expectations"
          copyText={ice.map(mirrorCopy).join("\n\n")}
        >
          <AnswerList answers={ice} />
        </CollapsibleCard>

        <ClinicianCard
          title="AI encounter summary"
          subtitle="Written in English by the nurse-review agent"
          tone="cream"
          copyText={state.encounterSummary ?? ""}
        >
          {state.encounterSummary ? (
            <p className="encounter-summary">{state.encounterSummary}</p>
          ) : (
            <Placeholder detail="Generated once the patient reaches review." />
          )}
        </ClinicianCard>

        <div className="complete-card">
          <div>
            <small>Encounter lifecycle</small>
            <strong>{formatStatus(state.status)}</strong>
          </div>
          <button
            type="button"
            className="complete-button"
            disabled={state.status !== "AWAITING_REVIEW" || state.busy}
            onClick={onComplete}
          >
            Mark complete
          </button>
        </div>
      </div>
    </section>
  );
}

function ClinicianCard({
  title,
  subtitle,
  tone,
  copyText,
  children,
}: {
  title: string;
  subtitle?: string;
  tone: "cream" | "lavender" | "red";
  copyText: string;
  children: ReactNode;
}) {
  return (
    <article className="clinician-card">
      <div className={`clinician-card-header ${tone}`}>
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        <CopyButton text={copyText} />
      </div>
      <div className="clinician-card-body">{children}</div>
    </article>
  );
}

function CollapsibleCard({
  title,
  copyText,
  children,
}: {
  title: string;
  copyText: string;
  children: ReactNode;
}) {
  const [expanded, setExpanded] = useState(true);
  return (
    <article className="clinician-card">
      <div className="clinician-card-header lavender">
        <button
          className="collapsible-trigger"
          type="button"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
        >
          <h2>{title}</h2>
          <span className={expanded ? "chevron expanded" : "chevron"}>⌄</span>
        </button>
        <CopyButton text={copyText} />
      </div>
      {expanded ? <div className="clinician-card-body">{children}</div> : null}
    </article>
  );
}

function AnswerList({
  answers,
  redFlags = false,
}: {
  answers: MirrorAnswer[];
  redFlags?: boolean;
}) {
  if (!answers.length) return <Placeholder />;
  return (
    <div className="answer-list">
      {answers.map((answer) => (
        <div
          className={`answer-row ${redFlags && isAffirmative(answer) ? "raised" : ""}`}
          key={answer.id}
        >
          <TranslatedAnswer answer={answer} />
        </div>
      ))}
    </div>
  );
}

/**
 * English only. This pane is read by clinicians who do not speak the patient's
 * language, so it never renders `nativePrompt` or `nativeValue` — an
 * untranslated answer is reported as a gap rather than shown in a language the
 * reader cannot use. Patient names are the one exception (see `patient-name`).
 */
function TranslatedAnswer({
  answer,
  prominent = false,
}: {
  answer: MirrorAnswer;
  prominent?: boolean;
}) {
  const english = answer.englishValue;
  return (
    <div className={prominent ? "translated-answer prominent" : "translated-answer"}>
      <span>{answer.englishPrompt}</span>
      {english !== null ? (
        <strong>{english}</strong>
      ) : (
        <strong className="untranslated-note">Not available in English</strong>
      )}
    </div>
  );
}

function BioItem({
  label,
  value,
  wide = false,
}: {
  label: string;
  value: string;
  wide?: boolean;
}) {
  return (
    <div className={wide ? "bio-item wide" : "bio-item"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Placeholder({
  text = "Not collected yet",
  detail,
}: {
  text?: string;
  detail?: string;
}) {
  return (
    <div className="neutral-placeholder">
      <span>{text}</span>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="copy-button"
      aria-label="Copy section"
      disabled={!text}
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1200);
      }}
    >
      {copied ? "✓" : "⧉"}
    </button>
  );
}

function ageFromYear(value: string): number | null {
  if (!/^\d{4}$/.test(value)) return null;
  return new Date().getFullYear() - Number(value);
}

function formatPhase(phase: string | null | undefined): string {
  if (!phase) return "Onboarding";
  return phase
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatStatus(status: string | null): string {
  return status?.replace(/_/g, " ") ?? "NOT STARTED";
}

function statusTone(status: string | null): string {
  if (status === "COMPLETED") return "complete";
  if (status === "AWAITING_REVIEW") return "review";
  if (status === "IN_PROGRESS") return "active";
  return "idle";
}

function capitalize(value: string): string {
  return value ? value[0].toUpperCase() + value.slice(1) : "";
}

function mirrorCopy(answer: MirrorAnswer | undefined): string {
  if (!answer) return "Not collected yet";
  // English only — this text is pasted into clinical notes.
  const value = answer.englishValue ?? "Not available in English";
  return `${answer.englishPrompt}: ${value}`;
}

function isAffirmative(answer: MirrorAnswer): boolean {
  return ["yes", "true"].includes(
    (answer.englishValue ?? answer.nativeValue).toLowerCase(),
  );
}
