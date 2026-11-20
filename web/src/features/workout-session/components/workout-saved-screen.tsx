import Link from "next/link";

import type { Exercise, SetRead, Workout } from "@spottr/api-client";

import { buttonClasses, CheckIcon } from "~/components/ui";

import {
  exerciseNameById,
  formatDuration,
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

/** Confirmation seal. A check inside a ring, with nothing to collide. */
function SavedSeal() {
  return (
    <span
      role="img"
      aria-label="Workout saved"
      className="bg-accent/10 ring-accent relative grid size-12 shrink-0 place-items-center rounded-full ring-2 sm:size-14"
    >
      <span
        aria-hidden="true"
        className="border-accent/40 absolute inset-1.5 rounded-full border border-dashed"
      />
      <CheckIcon className="text-accent relative size-5 sm:size-6" />
    </span>
  );
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
  const topSet = workout.sets.reduce<SetRead | null>((top, set) => {
    if (
      top === null ||
      set.weight > top.weight ||
      (set.weight === top.weight && set.reps > top.reps)
    ) {
      return set;
    }
    return top;
  }, null);
  // created_at is the save time, so this is the session length. Seeded rows
  // have a months-old performed_at; keep implausible durations off screen.
  const durationSeconds =
    (Date.parse(workout.created_at) - Date.parse(workout.performed_at)) / 1000;
  const showDuration =
    Number.isFinite(durationSeconds) &&
    durationSeconds >= 1 &&
    durationSeconds <= 12 * 3600;

  return (
    <div
      data-testid="workout-saved"
      className="flex max-w-[720px] flex-col gap-4"
    >
      <header
        data-testid="saved-workout-summary"
        className="flex flex-col gap-2 pb-2"
      >
        <div className="flex items-center justify-between gap-4">
          <h1
            aria-label={`Workout saved — ${formatKg(tonnage)} kilograms lifted`}
            className="display min-w-0 text-[40px] leading-none sm:text-[52px]"
          >
            {formatKg(tonnage)}
            <span className="text-ash-300 ml-2 align-baseline text-[15px] tracking-[0.02em] sm:text-[18px]">
              kg
            </span>
          </h1>
          <SavedSeal />
        </div>
        <p className="num text-bone-300 text-[13px] leading-relaxed">
          {workout.sets.length} sets · {groups.length}{" "}
          {groups.length === 1 ? "exercise" : "exercises"}
          {topSet
            ? ` · top set ${formatKg(topSet.weight)} × ${topSet.reps}`
            : ""}
        </p>
        <p className="num text-ash-400 text-pretty text-[12px] leading-relaxed">
          {formatPerformedAt(workout.performed_at)}
          {showDuration ? ` · ${formatDuration(durationSeconds)}` : ""}
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
