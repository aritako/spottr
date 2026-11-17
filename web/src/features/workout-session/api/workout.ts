import {
  ApiError,
  createAppClient,
  type Exercise,
  type Workout,
} from "@spottr/api-client";

import { env } from "~/env";

import { loadExerciseCatalog } from "./exercises";

export interface WorkoutDetail {
  workout: Workout;
  exercises: Exercise[];
}

/** Fetch one workout plus the catalog used to resolve exercise names. */
export async function loadWorkoutDetail(id: number): Promise<WorkoutDetail> {
  const client = createAppClient({ baseUrl: env.SPOTTR_API_URL });
  const [workout, exercises] = await Promise.all([
    client.getWorkout(id),
    loadExerciseCatalog(),
  ]);
  if (!workout) {
    throw new ApiError(404, "Workout not found.");
  }
  return { workout, exercises };
}
