import type {
  AskCoachResponse,
  CreateExerciseInput,
  CreateWorkoutInput,
  EntityCreated,
  Exercise,
  PaginationParams,
  Workout,
} from "./types";

export class SpottrApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
    message = `Spottr API request failed (${status}): ${detail}`,
  ) {
    super(message);
    this.name = "SpottrApiError";
  }
}

export type FetchLike = (
  input: string,
  init?: RequestInit,
) => Promise<Response>;

export interface SpottrClientOptions {
  /** Base URL of the FastAPI service, e.g. http://localhost:8000. */
  baseUrl: string;
  fetch?: FetchLike;
  headers?: HeadersInit;
  /** Abort a request after this many milliseconds. Defaults to 30s. */
  timeoutMs?: number;
}

function buildQuery(params: PaginationParams | undefined): string {
  const query = new URLSearchParams();
  if (params?.page !== undefined) query.set("page", String(params.page));
  if (params?.pageSize !== undefined) {
    query.set("page_size", String(params.pageSize));
  }
  const value = query.toString();
  return value ? `?${value}` : "";
}

async function readError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (
      body &&
      typeof body === "object" &&
      "detail" in body &&
      typeof body.detail === "string"
    ) {
      return body.detail;
    }
    return JSON.stringify(body).slice(0, 500);
  } catch {
    return response.statusText || "Unknown error";
  }
}

export function createSpottrClient({
  baseUrl,
  fetch: fetchImpl,
  headers,
  timeoutMs = 30_000,
}: SpottrClientOptions) {
  const root = baseUrl.replace(/\/+$/, "");
  const doFetch: FetchLike = fetchImpl ?? globalThis.fetch;

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await doFetch(`${root}${path}`, {
        ...init,
        cache: init?.cache ?? "no-store",
        signal: init?.signal ?? controller.signal,
        headers: {
          Accept: "application/json",
          ...(init?.body ? { "Content-Type": "application/json" } : {}),
          ...headers,
          ...init?.headers,
        },
      });

      if (!response.ok) {
        throw new SpottrApiError(response.status, await readError(response));
      }

      if (response.status === 204) {
        return undefined as T;
      }

      return (await response.json()) as T;
    } finally {
      clearTimeout(timeout);
    }
  }

  return {
    getHealth: () => request<{ status: string }>("/health"),

    listExercises: (params?: PaginationParams) =>
      request<Exercise[]>(`/exercises${buildQuery(params)}`),

    getExercise: (id: number) => request<Exercise | null>(`/exercises/${id}`),

    createExercise: (input: CreateExerciseInput) =>
      request<EntityCreated>("/exercises", {
        method: "POST",
        body: JSON.stringify(input),
      }),

    listWorkouts: (params?: PaginationParams) =>
      request<Workout[]>(`/workouts${buildQuery(params)}`),

    getWorkout: (id: number) => request<Workout | null>(`/workouts/${id}`),

    createWorkout: (input: CreateWorkoutInput) =>
      request<EntityCreated>("/workouts", {
        method: "POST",
        body: JSON.stringify(input),
      }),

    askCoach: (question: string) =>
      request<AskCoachResponse>("/coach/ask", {
        method: "POST",
        body: JSON.stringify({ question }),
      }),
  };
}

export type SpottrClient = ReturnType<typeof createSpottrClient>;
