import type { components } from "@align/generated-types";
import type { Locale, PatientSex } from "./contracts";

type CreateResponse = components["schemas"]["CreateSessionResponse"];
type GetResponse = components["schemas"]["GetSessionResponse"];
type RespondResponse = components["schemas"]["RespondResponse"];
type CompleteResponse = components["schemas"]["CompleteResponse"];

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function requestJson<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  const text = await response.text();
  const body = text ? (JSON.parse(text) as unknown) : null;
  if (!response.ok) {
    const detail =
      body &&
      typeof body === "object" &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : response.statusText;
    throw new ApiError(response.status, detail || "Request failed");
  }
  return body as T;
}

export function createSession(locale: Locale, patientSex: PatientSex) {
  const query = new URLSearchParams({
    session_language: locale,
    patient_sex: patientSex,
  });
  return requestJson<CreateResponse>(`/api/demo/sessions?${query}`, {
    method: "POST",
  });
}

export function getSession(sessionId: string) {
  return requestJson<GetResponse>(
    `/api/demo/sessions/${encodeURIComponent(sessionId)}`,
  );
}

export function respond(
  sessionId: string,
  answer: Record<string, unknown>,
) {
  return requestJson<RespondResponse>(
    `/api/demo/sessions/${encodeURIComponent(sessionId)}/respond`,
    {
      method: "POST",
      body: JSON.stringify({ answer }),
    },
  );
}

export function completeSession(sessionId: string) {
  return requestJson<CompleteResponse>(
    `/api/demo/clinician/sessions/${encodeURIComponent(sessionId)}/complete`,
    { method: "POST" },
  );
}
