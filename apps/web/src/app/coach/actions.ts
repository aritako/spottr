"use server";

import {
  createSpottrClient,
  SpottrApiError,
  type AskCoachResponse,
} from "@spottr/api-client";

import { env } from "~/env";
import { MAX_QUESTION_LENGTH } from "~/lib/coach";
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

  if (question.length > MAX_QUESTION_LENGTH) {
    return {
      status: "error",
      question: "",
      message: `Keep questions under ${MAX_QUESTION_LENGTH} characters.`,
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
        message: `The coach service returned an error (${error.status}). Please try again.`,
      };
    }

    return {
      status: "error",
      question,
      message:
        "Could not reach the coach service. Make sure the backend is running and try again.",
    };
  }
}
