"use server";

import {
  createSpottrClient,
  SpottrApiError,
  type AskCoachResponse,
} from "@spottr/api-client";

import { env } from "~/env";
import { readStringField } from "~/lib/form-value";

export type CoachState =
  | { status: "idle" }
  | { status: "answer"; question: string; response: AskCoachResponse }
  | { status: "error"; question: string; message: string };

export async function askCoach(
  _previousState: CoachState,
  formData: FormData,
): Promise<CoachState> {
  const question = readStringField(formData, "suggestion", "question");

  if (!question) {
    return {
      status: "error",
      question: "",
      message: "Ask the coach a question first.",
    };
  }

  const client = createSpottrClient({ baseUrl: env.SPOTTR_API_URL });

  try {
    const response = await client.askCoach(question);
    return { status: "answer", question, response };
  } catch (error) {
    if (error instanceof SpottrApiError) {
      return {
        status: "error",
        question,
        message: `The coach API returned ${error.status}: ${error.detail.slice(0, 240)}`,
      };
    }

    return {
      status: "error",
      question,
      message: `Could not reach the Spottr API at ${env.SPOTTR_API_URL}. Start the backend and try again.`,
    };
  }
}
