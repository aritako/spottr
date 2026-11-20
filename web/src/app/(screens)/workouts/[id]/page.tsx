import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ApiError } from "@spottr/api-client";

import {
  WorkoutLoadError,
  WorkoutSavedScreen,
} from "~/features/workout-session";
import { loadWorkoutDetail } from "~/features/workout-session/api/workout";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Workout saved" };

export default async function WorkoutPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const workoutId = Number(id);
  if (!Number.isInteger(workoutId) || workoutId <= 0) {
    notFound();
  }

  try {
    const { workout, exercises } = await loadWorkoutDetail(workoutId);
    return <WorkoutSavedScreen workout={workout} exercises={exercises} />;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    return <WorkoutLoadError />;
  }
}
