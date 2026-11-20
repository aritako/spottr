import Link from "next/link";

import type { Exercise, SetRead, Workout } from "@spottr/api-client";

import { buttonClasses, CheckIcon } from "~/components/ui";

import {
  exerciseNameById,
  formatKg,
  formatPerformedAt,
  type RelogHandoff,
} from "../model/session";
import { DeleteAndRelog } from "./delete-and-relog";

interface ExerciseGroup {
  exerciseId: number;
  sets: SetRead[];
}

function groupSets(workout: Workout): ExerciseGroup[] {
  const order: number[] = [];
  const groups = new Map<number, SetRead[]>();
  // The API's set_index is global for explicit zeros, and has no guaranteed
  // order on read. Insertion order (id) is the set order the user logged.
  const sorted = [...workout.sets].sort((a, b) => a.id - b.id);
  for (const set of sorted) {
    const existing = groups.get(set.exercise_id);
    if (existing) {
      existing.push(set);
    } else {
      groups.set(set.exercise_id, [set]);
      order.push(set.exercise_id);
    }
  }
  return order.map((exerciseId) => ({
    exerciseId,
    sets: groups.get(exerciseId) ?? [],
  }));
}

function SetLine({ set, index }: { set: SetRead; index: number }) {
  return (
    <li className="flex items-baseline justify-between gap-3 py-1">
      <span className="num text-ash-400 w-4 text-[11px]">{index + 1}</span>
      <span className="num text-[14px]">
        {formatKg(set.weight)} × {set.reps}
        {set.rpe !== null ? (
          <span className="text-ash-400 text-[12px]"> @ {set.rpe}</span>
        ) : null}
      </span>
    </li>
  );
}

function toHandoff(workout: Workout): RelogHandoff {
  return {
    version: 1,
    performedAt: workout.performed_at,
    notes: workout.notes ?? "",
    exercises: groupSets(workout).map((group) => ({
      exerciseId: group.exerciseId,
      sets: group.sets.map((set) => ({
        weight: String(set.weight),
        reps: String(set.reps),
        rpe: set.rpe === null ? "" : String(set.rpe),
        completed: true,
      })),
    })),
  };
}

/** Confirmation screen after a successful save. */
export function WorkoutSavedScreen({
  workout,
  exercises,
}: {
  workout: Workout;
  exercises: Exercise[];
}) {
  const groups = groupSets(workout);
  const tonnage = workout.sets.reduce(
    (total, set) => total + set.weight * set.reps,
    0,
  );
  return (
    <div
      data-testid="workout-saved"
      className="flex max-w-[720px] flex-col gap-4"
    >
      <header
        data-testid="saved-workout-summary"
        className="flex flex-col items-center gap-2 pb-3 text-center"
      >
        <h1
          aria-label={`Workout saved — ${formatKg(tonnage)} kilograms lifted`}
          className="display text-[40px] leading-none sm:text-[52px]"
        >
          {formatKg(tonnage)}
          <span className="num text-ash-300 ml-2 align-baseline text-[13px] font-normal tracking-[0.02em] sm:text-[16px]">
            kg lifted
          </span>
        </h1>
        <p className="num text-bone-300 text-[13px] leading-relaxed">
          {workout.sets.length} sets · {groups.length}{" "}
          {groups.length === 1 ? "exercise" : "exercises"}
        </p>
        <p className="num text-ash-400 inline-flex items-center gap-1.5 text-[12px] leading-relaxed">
          <CheckIcon className="text-accent size-3.5" />
          Completed {formatPerformedAt(workout.performed_at)}
        </p>
      </header>

      <div className="rounded-panel bg-lab-800 divide-lab-700 divide-y overflow-hidden">
        {groups.map((group) => (
          <section key={group.exerciseId} className="px-5 py-4">
            <h2 className="display text-[15px] leading-none">
              {exerciseNameById(exercises, group.exerciseId)}
            </h2>
            <ul className="mt-2 flex flex-col">
              {group.sets.map((set, index) => (
                <SetLine key={set.id} set={set} index={index} />
              ))}
            </ul>
          </section>
        ))}
      </div>

      {workout.notes ? (
        <p className="text-bone-300 px-1 text-sm leading-relaxed">
          {workout.notes}
        </p>
      ) : null}

      <div className="rounded-panel bg-lab-800 flex flex-wrap items-center justify-between gap-3 px-5 py-4">
        <span className="text-ash-400 text-[12px]">Logged a mistake?</span>
        <DeleteAndRelog workoutId={workout.id} handoff={toHandoff(workout)} />
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Link
          href="/workouts/start"
          className={buttonClasses({ variant: "primary", size: "md" })}
        >
          Log another workout
        </Link>
        <Link
          href="/"
          className={buttonClasses({ variant: "secondary", size: "md" })}
        >
          Back to home
        </Link>
      </div>
    </div>
  );
}
