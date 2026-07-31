"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

/**
 * First-run guide for people being shown the demo.
 *
 * Marketing copy is quoted from the sections the Align-Pilot-V2 landing page
 * actually renders — `(marketing)/page.tsx` mounts only HeroSection,
 * GPPainPointsSection, HowItWorksSection, WhoItsForSection and
 * PilotSignupSection. Do not source copy from `about-section.tsx`,
 * `our-journey-section.tsx` or `team-section.tsx`: those components exist in
 * that repo but are imported nowhere, and their dates are stale.
 *
 * Framing is retrospective: Align piloted in urgent care March–June 2026 and
 * the company has since wound down, so this is a portfolio piece. Marketing
 * claims stay in the past tense and nothing promises future work.
 *
 * The last two slides describe THIS build, not the pilot product — keep them
 * honest when the backend changes.
 *
 * English only: this addresses the person running the demo, not the patient.
 * The patient pane's own copy stays localised.
 */

const STORAGE_KEY = "align-demo-guide-seen-v1";

type Slide = {
  eyebrow: string;
  title: string;
  lede?: string;
  points?: { title: string; body: string }[];
  note?: string;
  link?: { href: string; label: string };
};

const SLIDES: Slide[] = [
  {
    eyebrow: "Welcome",
    title: "AI that prepares your next patient before they walk in.",
    lede: "Align provides a full preconsultation summary the moment a patient arrives — so every 15 minutes counts.",
  },
  {
    eyebrow: "Who we are",
    title: "Healthcare system is stretched thin.",
    lede: "Clinicians are burning out, and patients aren't getting the time they need. Align works simultaneously for patients and clinicians, connecting the two sides of every consultation before it even starts.",
    points: [
      {
        title: "Time is the enemy",
        body: "By the time a clinician gathers history, reviews notes, and understands the complaint, the clock is already running out.",
      },
      {
        title: "Communication barriers",
        body: "Patients who don't speak English fluently or have low health literacy struggle to communicate symptoms clearly — creating confusion, missed information, and fatigue on both sides.",
      },
      {
        title: "Red flags get missed",
        body: "In a busy clinic, critical warning signs can be overlooked in the noise. Clinicians need a system that catches the things no one has time to ask about.",
      },
    ],
    note: "Align piloted in urgent care from March to June 2026. Physio was next.",
  },
  {
    eyebrow: "Left pane",
    title: "The patient app",
    lede: "Walk-in patients with no appointment: QR code check-in, then a complete preconsult summary waiting for the clinician before the patient enters the room.",
    points: [
      {
        title: "Adaptive questioning",
        body: "Questions are generated per patient from their complaint — not a fixed form. Each answer reshapes what comes next.",
      },
      {
        title: "Multilingual by default",
        body: "The patient picks their language and everything follows: prompts, options, and the body diagram.",
      },
      {
        title: "Body diagram",
        body: "Tap the site of the problem. Suggested regions are pre-highlighted from the complaint.",
      },
      {
        title: "Red flag screening",
        body: "Critical symptom patterns are screened for explicitly and surfaced to the clinician.",
      },
    ],
  },
  {
    eyebrow: "Right pane",
    title: "The clinician dashboard",
    lede: "Updates live as the patient answers — no refresh, no waiting for submission.",
    points: [
      {
        title: "Structured summaries",
        body: "Chief complaint, ICE, body site, medications and red flags organised into cards reviewable in seconds.",
      },
      {
        title: "Always in English",
        body: "A patient answering in Korean produces an English dashboard. Free text is translated server-side; options carry their English label.",
      },
      {
        title: "Copy to notes",
        body: "Every card copies out as clean English text for the patient record.",
      },
    ],
  },
  {
    eyebrow: "About this build",
    title: "What is real here, and what is not",
    lede: "Nothing on either side is mocked up in the frontend. The question engine runs for real against Azure OpenAI.",
    points: [
      {
        title: "Real",
        body: "Classifier, adaptive question generation, red flag screening, translation and the clinician mirror all execute live. LangGraph drives the session; FastAPI serves it.",
      },
      {
        title: "Designed, not connected",
        body: "The repo carries a full Postgres schema and Alembic migrations: three least-privilege roles and forced row-level security on all 17 tenant-scoped tables, with no BYPASSRLS anywhere. The demo runs sessions in memory instead, so a restart clears them.",
      },
      {
        title: "Out of scope",
        body: "Auth, the patient queue, print-ready records and clinician notes belonged to the wider pilot product and were never part of this build.",
      },
    ],
    note: "Both panes share one browser session so the flow can be demonstrated end to end. In the pilot the clinician view was a separate authenticated app.",
  },
  {
    eyebrow: "Credits",
    title: "Built by Manseung Choi",
    lede: "This pilot and demo system was built by Manseung Choi, ex-cofounder of Align.",
    link: { href: "https://manseungchoi.com", label: "manseungchoi.com" },
    note: "You are welcome to visit my webpage to view my work.",
  },
];

// localStorage is not available during the server render, so "has this been
// dismissed?" is read through useSyncExternalStore rather than in an effect.
// The server snapshot reports "dismissed" so the markup React renders on the
// server is the small reopen button, never a modal it would have to unmount.
const listeners = new Set<() => void>();
let dismissedCache: boolean | null = null;

function subscribeDismissed(onChange: () => void) {
  listeners.add(onChange);
  return () => listeners.delete(onChange);
}

function readDismissed(): boolean {
  if (dismissedCache === null) {
    try {
      dismissedCache = window.localStorage.getItem(STORAGE_KEY) === "1";
    } catch {
      // Private mode / storage disabled — show the guide, just don't remember.
      dismissedCache = false;
    }
  }
  return dismissedCache;
}

function markDismissed() {
  dismissedCache = true;
  try {
    window.localStorage.setItem(STORAGE_KEY, "1");
  } catch {
    // Non-fatal: the guide reopens next visit.
  }
  for (const listener of listeners) listener();
}

export function WelcomeGuide() {
  const dismissed = useSyncExternalStore(
    subscribeDismissed,
    readDismissed,
    () => true,
  );
  const [reopened, setReopened] = useState(false);
  const [index, setIndex] = useState(0);
  const open = reopened || !dismissed;

  const close = useCallback(() => {
    setReopened(false);
    markDismissed();
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
      if (event.key === "ArrowRight") {
        setIndex((i) => Math.min(i + 1, SLIDES.length - 1));
      }
      if (event.key === "ArrowLeft") setIndex((i) => Math.max(i - 1, 0));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close]);

  if (!open) {
    return (
      <button
        type="button"
        className="guide-reopen"
        onClick={() => {
          setIndex(0);
          setReopened(true);
        }}
        aria-label="About this demo"
        title="About this demo"
      >
        ?
      </button>
    );
  }

  const slide = SLIDES[index];
  const last = index === SLIDES.length - 1;

  return (
    <div
      className="guide-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="guide-title"
      onClick={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <div className="guide-card">
        <button
          type="button"
          className="guide-close"
          onClick={close}
          aria-label="Close"
        >
          ✕
        </button>

        <span className="guide-eyebrow">{slide.eyebrow}</span>
        <h2 id="guide-title" className="guide-title">
          {slide.title}
        </h2>
        {slide.lede ? <p className="guide-lede">{slide.lede}</p> : null}

        {slide.points ? (
          <ul className="guide-points">
            {slide.points.map((point) => (
              <li key={point.title}>
                <strong>{point.title}</strong>
                <span>{point.body}</span>
              </li>
            ))}
          </ul>
        ) : null}

        {slide.link ? (
          <a
            className="guide-link"
            href={slide.link.href}
            target="_blank"
            rel="noopener noreferrer"
          >
            {slide.link.label}
            <span aria-hidden>↗</span>
          </a>
        ) : null}

        {slide.note ? <p className="guide-note">{slide.note}</p> : null}

        <div className="guide-footer">
          <div className="guide-dots" role="tablist" aria-label="Guide sections">
            {SLIDES.map((item, dotIndex) => (
              <button
                key={item.eyebrow}
                type="button"
                role="tab"
                aria-selected={dotIndex === index}
                aria-label={item.eyebrow}
                className={dotIndex === index ? "active" : ""}
                onClick={() => setIndex(dotIndex)}
              />
            ))}
          </div>
          <div className="guide-actions">
            {index > 0 ? (
              <button
                type="button"
                className="guide-back"
                onClick={() => setIndex((i) => i - 1)}
              >
                Back
              </button>
            ) : null}
            <button
              type="button"
              className="guide-next"
              onClick={() => (last ? close() : setIndex((i) => i + 1))}
            >
              {last ? "Start the demo" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
