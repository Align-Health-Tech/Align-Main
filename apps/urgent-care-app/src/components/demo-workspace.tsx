"use client";

import { useEffect, useReducer } from "react";
import { ClinicianPane } from "./clinician-pane";
import { PatientPane } from "./patient-pane";
import { WelcomeGuide } from "./welcome-guide";
import {
  ApiError,
  completeSession,
  createSession,
  getSession,
  respond,
} from "../lib/api-client";
import type { BodySelection, Locale, Pane } from "../lib/contracts";
import {
  INITIAL_STATE,
  buildMirrorAnswers,
  clearStoredState,
  demoReducer,
  loadStoredState,
  saveStoredState,
} from "../lib/demo-state";
import { COPY } from "../lib/locales";

export function DemoWorkspace() {
  const [state, dispatch] = useReducer(demoReducer, INITIAL_STATE);
  const copy = COPY[state.locale];

  useEffect(() => {
    const stored = loadStoredState();
    dispatch({ type: "HYDRATE", state: stored });
    if (!stored?.sessionId) return;

    void getSession(stored.sessionId)
      .then((response) => {
        if (
          response.next_step.phase === "consent" &&
          stored.stage === "identity"
        ) {
          dispatch({
            type: "SESSION_CREATED",
            sessionId: stored.sessionId as string,
            nextStep: response.next_step,
            status: response.status,
          });
          return;
        }
        dispatch({
          type: "SYNC_SESSION",
          nextStep: response.next_step,
          status: response.status,
          mirror: response.mirror,
        });
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 404) {
          clearStoredState();
          dispatch({ type: "RESET" });
          dispatch({
            type: "SET_ERROR",
            error: COPY[stored.locale ?? "en"].staleSession,
          });
          return;
        }
        dispatch({
          type: "SET_ERROR",
          error: COPY[stored.locale ?? "en"].genericError,
        });
      });
  }, []);

  useEffect(() => {
    saveStoredState(state);
  }, [state]);

  const handleMutationError = async (
    error: unknown,
    sessionId: string | null,
  ) => {
    if (error instanceof ApiError && error.status === 409 && sessionId) {
      try {
        const current = await getSession(sessionId);
        dispatch({
          type: "SYNC_SESSION",
          nextStep: current.next_step,
          status: current.status,
          mirror: current.mirror,
        });
        return;
      } catch {
        dispatch({ type: "SET_ERROR", error: copy.genericError });
        return;
      }
    }
    dispatch({ type: "SET_ERROR", error: copy.genericError });
  };

  const startEncounter = async () => {
    if (!state.demographics.patientSex) return;
    dispatch({ type: "SET_BUSY", busy: true });
    let activeSessionId = state.sessionId;
    try {
      if (!activeSessionId) {
        const created = await createSession(
          state.locale,
          state.demographics.patientSex,
        );
        activeSessionId = created.session_id;
        dispatch({
          type: "SESSION_CREATED",
          sessionId: activeSessionId,
          nextStep: created.next_step,
          status: created.status,
        });
      }
      const accepted = await respond(activeSessionId, {
        answers: [{ question_id: "consent_privacy", value: true }],
      });
      dispatch({
        type: "SYNC_SESSION",
        nextStep: accepted.next_step,
        status: accepted.status,
      });
    } catch (error) {
      await handleMutationError(error, activeSessionId);
    }
  };

  const submitAnswer = async (
    answer: Record<string, unknown>,
    bodySelection?: BodySelection,
  ) => {
    if (!state.sessionId || !state.nextStep) return;
    const submittedStep = state.nextStep;
    dispatch({ type: "SET_BUSY", busy: true });
    try {
      const response = await respond(state.sessionId, answer);
      dispatch({
        type: "ANSWER_SAVED",
        nextStep: response.next_step,
        status: response.status,
        mirrorAnswers: buildMirrorAnswers(
          submittedStep,
          answer,
          state.locale,
        ),
        mirror: response.mirror,
        bodySelection,
      });
    } catch (error) {
      await handleMutationError(error, state.sessionId);
    }
  };

  const setPane = async (pane: Pane) => {
    dispatch({ type: "SET_PANE", pane });
    if (pane !== "clinician" || !state.sessionId) return;
    try {
      const current = await getSession(state.sessionId);
      dispatch({
        type: "SYNC_SESSION",
        nextStep: current.next_step,
        status: current.status,
        mirror: current.mirror,
      });
    } catch {
      // The local mirror remains useful when a status-only refresh fails.
    }
  };

  const markComplete = async () => {
    if (!state.sessionId) return;
    dispatch({ type: "SET_BUSY", busy: true });
    try {
      const result = await completeSession(state.sessionId);
      dispatch({ type: "MARK_COMPLETED", status: result.status });
    } catch (error) {
      await handleMutationError(error, state.sessionId);
    }
  };

  const restart = () => {
    if (!window.confirm(copy.restartConfirm)) return;
    clearStoredState();
    dispatch({ type: "RESET" });
  };

  return (
    <main className="demo-shell">
      <nav className="mobile-pane-toggle" aria-label="Workspace view">
        {(["patient", "clinician"] as const).map((pane) => (
          <button
            key={pane}
            type="button"
            className={state.activePane === pane ? "active" : ""}
            onClick={() => void setPane(pane)}
          >
            {pane === "patient" ? copy.patientPane : copy.clinicianPane}
          </button>
        ))}
      </nav>
      <div
        className={`workspace-pane patient-workspace ${state.activePane === "patient" ? "mobile-active" : ""}`}
      >
        <PatientPane
          state={state}
          onLocale={(locale: Locale) =>
            dispatch({ type: "SET_LOCALE", locale })
          }
          onConsentAccepted={(accepted) =>
            dispatch({ type: "ACCEPT_CONSENT", accepted })
          }
          onShowIdentity={() => dispatch({ type: "SHOW_IDENTITY" })}
          onDemographics={(values) =>
            dispatch({ type: "UPDATE_DEMOGRAPHICS", values })
          }
          onStartEncounter={() => void startEncounter()}
          onSubmitAnswer={(answer, bodySelection) =>
            void submitAnswer(answer, bodySelection)
          }
          onRestart={restart}
        />
      </div>
      <div
        className={`workspace-pane clinician-workspace ${state.activePane === "clinician" ? "mobile-active" : ""}`}
      >
        <ClinicianPane
          state={state}
          onComplete={() => void markComplete()}
        />
      </div>
      <WelcomeGuide />
    </main>
  );
}
