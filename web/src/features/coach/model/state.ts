import type { AskCoachResponse } from "@spottr/api-client";

export type CoachState =
  | { status: "idle" }
  | { status: "answer"; question: string; response: AskCoachResponse }
  | { status: "error"; question: string; message: string };

export const initialCoachState: CoachState = { status: "idle" };
