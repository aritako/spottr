"use server";

import { ApiError, createAppClient } from "@spottr/api-client";
import { z } from "zod";

import { env } from "~/env";
import { readStringField } from "~/lib/form-value";

import {
  MAX_NOTES_LENGTH,
  MAX_REPS,
  MAX_RPE,
  MAX_SETS_PER_SAVE,
  MAX_WEIGHT_KG,
} from "./model/constants";
import type { DeleteWorkoutState, SaveWorkoutState } from "./model/state";

function hasTwoDecimals(value: number): boolean {
  return Math.abs(value * 100 - Math.round(value * 100)) < 1e-6;
}

const SetPayloadSchema = z.object({
  exerciseId: z.number().int().positive(),
  weight: z
    .number()
    .min(0)
    .max(MAX_WEIGHT_KG)
    .refine(hasTwoDecimals, { message: "at most 2 decimals" }),
  reps: z.number().int().min(1).max(MAX_REPS),
  rpe: z.number().min(0).max(MAX_RPE).nullable(),
  setIndex: z.number().int().min(0),
});

const SessionPayloadSchema = z.object({
  performedAt: z.string().refine((value) => !Number.isNaN(Date.parse(value)), {
    message: "invalid timestamp",
  }),
  sets: z.array(SetPayloadSchema).min(1).max(MAX_SETS_PER_SAVE),
});

/** Single POST for the whole session. Client state is never cleared here. */
export async function saveWorkout(
  _previousState: SaveWorkoutState,
  formData: FormData,
): Promise<SaveWorkoutState> {
  if (formData.get("simulate_failure") !== null) {
    return {
      status: "error",
      message:
        "Simulated save failure (prototype control). The API was not called.",
    };
  }

  const notes = readStringField(formData, "notes");
  if (notes.length > MAX_NOTES_LENGTH) {
    return {
      status: "error",
      message: `Keep notes under ${MAX_NOTES_LENGTH} characters.`,
    };
  }

  let payload: unknown;
  try {
    payload = JSON.parse(readStringField(formData, "payload"));
  } catch {
    return {
      status: "error",
      message: "Could not read your session data.",
    };
  }

  const parsed = SessionPayloadSchema.safeParse(payload);
  if (!parsed.success) {
    return {
      status: "error",
      message:
        "Some sets need attention before saving (load 0–9999.99 kg, reps 1–999, RPE 0–10).",
    };
  }

  const client = createAppClient({ baseUrl: env.SPOTTR_API_URL });
  try {
    const created = await client.createWorkout({
      unit: "kg",
      notes: notes === "" ? null : notes,
      performed_at: parsed.data.performedAt,
      sets: parsed.data.sets.map((set) => ({
        exercise_id: set.exerciseId,
        weight: set.weight,
        reps: set.reps,
        rpe: set.rpe,
        set_index: set.setIndex,
      })),
    });
    return { status: "success", workoutId: created.id };
  } catch (error) {
    if (error instanceof ApiError) {
      return {
        status: "error",
        message: `Couldn't save this workout (API ${error.status}: ${error.detail}).`,
      };
    }
    return {
      status: "error",
      message: "Could not reach the workout service.",
    };
  }
}

/** Delete a saved workout so it can be re-logged. Handoff stays in the browser. */
export async function deleteWorkout(
  _previousState: DeleteWorkoutState,
  formData: FormData,
): Promise<DeleteWorkoutState> {
  const id = Number(readStringField(formData, "workout_id"));
  if (!Number.isInteger(id) || id <= 0) {
    return {
      status: "error",
      message: "Missing workout id. Nothing was deleted.",
    };
  }

  const client = createAppClient({ baseUrl: env.SPOTTR_API_URL });
  try {
    await client.deleteWorkout(id);
    return { status: "success" };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return {
        status: "error",
        message:
          "That workout was already gone (404). Your re-log draft is still in this browser.",
      };
    }
    if (error instanceof ApiError) {
      return {
        status: "error",
        message: `Couldn't delete this workout (API ${error.status}: ${error.detail}). Nothing was deleted.`,
      };
    }
    return {
      status: "error",
      message:
        "Could not reach the workout service. Nothing was deleted — try again.",
    };
  }
}
