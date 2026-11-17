import Link from "next/link";

import type { Exercise, SetRead, Workout } from "@spottr/api-client";

import { PageHeader } from "~/components/page-header";
import { buttonClasses, Card } from "~/components/ui";

import {
  exerciseNameById,
  formatCategory,
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

function SavedStamp() {
  return (
    <svg
      width="96"
      height="96"
      viewBox="0 0 100 100"
      role="img"
      aria-label="Workout saved stamp"
      className="shrink-0"
    >
      <circle
        cx="50"
        cy="50"
        r="46"
        fill="none"
        strokeWidth="3"
        className="stroke-accent"
      />
      <circle
        cx="50"
        cy="50"
        r="37"
        fill="none"
        strokeWidth="1.5"
        strokeDasharray="3 3.5"
        className="stroke-accent"
      />
      <text
        x="50"
        y="46"
        textAnchor="middle"
        fontFamily="Archivo, system-ui, sans-serif"
        fontWeight="900"
        fontSize="17"
        letterSpacing="1.5"
        className="fill-accent"
        style={{ fontStretch: "125%" }}
      >
        SAVED
      </text>
      <text
        x="50"
        y="63"
        textAnchor="middle"
        fontFamily="Martian Mono, ui-monospace, monospace"
        fontSize="9"
        letterSpacing="2"
        className="fill-ash-300"
      >
        LOGGED
      </text>
    </svg>
  );
}

function SetLine({ set, index }: { set: SetRead; index: number }) {
  return (
    <li className="border-lab-700 flex items-baseline justify-between gap-3 border-b py-2 last:border-0">
      <span className="num text-ash-300 text-[12px]">Set {index + 1}</span>
      <span className="num text-[14px]">
        {formatKg(set.weight)} × {set.reps}
        {set.rpe !== null ? (
          <span className="text-ash-300 text-[12px]"> @ {set.rpe}</span>
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

  return (
    <div data-testid="workout-saved" className="flex flex-col gap-4">
      <PageHeader eyebrow="Session complete" title="Workout saved" />

      <Card className="rounded-panel flex flex-col gap-5 p-[18px] sm:flex-row sm:items-center sm:gap-6">
        <SavedStamp />
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          <span className="eyebrow">
            Logged {formatPerformedAt(workout.performed_at)}
          </span>
          <p className="display text-[22px] leading-none">
            {groups.length} {groups.length === 1 ? "lift" : "lifts"} ·{" "}
            {workout.sets.length} sets
          </p>
          <p className="text-bone-300 text-sm leading-relaxed">
            {formatKg(tonnage)} kg moved
            {topSet
              ? ` · top set ${formatKg(topSet.weight)} × ${topSet.reps}`
              : ""}
            . All loads in kilograms.
          </p>
        </div>
      </Card>

      <div
        data-testid="saved-workout-summary"
        className="grid grid-cols-2 gap-3 sm:grid-cols-4"
      >
        {[
          { label: "Exercises", value: String(groups.length) },
          { label: "Sets", value: String(workout.sets.length) },
          { label: "Tonnage", value: `${formatKg(tonnage)} kg` },
          {
            label: "Top set",
            value: topSet ? `${formatKg(topSet.weight)} × ${topSet.reps}` : "—",
          },
        ].map((stat) => (
          <Card key={stat.label} className="flex flex-col gap-1 p-4">
            <span className="eyebrow">{stat.label}</span>
            <span className="num text-[18px] leading-none">{stat.value}</span>
          </Card>
        ))}
      </div>

      {workout.notes ? (
        <Card className="flex flex-col gap-1.5 p-[18px]">
          <span className="eyebrow">Session notes</span>
          <p className="text-bone-300 text-sm leading-relaxed">
            {workout.notes}
          </p>
        </Card>
      ) : null}

      <div className="flex flex-col gap-4">
        {groups.map((group) => (
          <Card key={group.exerciseId} className="p-[18px]">
            <div className="flex flex-col gap-1 pb-1">
              <h2 className="display text-[16px] leading-tight">
                {exerciseNameById(exercises, group.exerciseId)}
              </h2>
              <span className="eyebrow normal-case tracking-normal">
                {formatCategory(
                  exercises.find((entry) => entry.id === group.exerciseId)
                    ?.category ?? null,
                )}
              </span>
            </div>
            <ul>
              {group.sets.map((set, index) => (
                <SetLine key={set.id} set={set} index={index} />
              ))}
            </ul>
          </Card>
        ))}
      </div>

      <Card className="rounded-panel flex flex-col gap-3 p-[18px]">
        <div className="flex flex-col gap-1">
          <span className="eyebrow">Need to fix something?</span>
          <p className="text-bone-300 text-sm leading-relaxed">
            There is no edit endpoint in this prototype, so corrections work as
            delete-and-re-log: the saved workout is permanently deleted, then
            its sets reopen in the builder for editing.
          </p>
        </div>
        <DeleteAndRelog workoutId={workout.id} handoff={toHandoff(workout)} />
      </Card>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Link
          href="/"
          className={buttonClasses({ variant: "secondary", size: "md" })}
        >
          Back to home
        </Link>
        <Link
          href="/workouts/start"
          className={buttonClasses({ variant: "primary", size: "md" })}
        >
          Log another workout
        </Link>
      </div>
    </div>
  );
}
