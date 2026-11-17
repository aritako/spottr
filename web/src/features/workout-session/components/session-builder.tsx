"use client";

import { useActionState, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import type { Exercise } from "@spottr/api-client";

import { PageHeader } from "~/components/page-header";
import { BarbellIcon, Button, EmptyState, PlusIcon } from "~/components/ui";

import { saveWorkout } from "../actions";
import { MAX_NOTES_LENGTH } from "../model/constants";
import {
  buildSetsPayload,
  clearRelogHandoff,
  computeTotals,
  exerciseNameById,
  formatKg,
  readRelogHandoff,
  validateSession,
  type DraftExercise,
  type RelogHandoff,
} from "../model/session";
import { initialSaveState } from "../model/state";
import { ExercisePicker } from "./exercise-picker";
import { SetEditor } from "./set-editor";
import { SessionSummary } from "./session-summary";

function blankSet(key: string) {
  return { key, weight: "", reps: "", rpe: "" };
}

function toDraft(handoff: RelogHandoff, catalog: Exercise[]): DraftExercise[] {
  const known = new Set(catalog.map((entry) => entry.id));
  return handoff.exercises
    .filter((entry) => known.has(entry.exerciseId))
    .map((entry, blockIndex) => ({
      key: `relog-${blockIndex}`,
      exerciseId: entry.exerciseId,
      sets: entry.sets.map((set, setIndex) => ({
        key: `relog-${blockIndex}-${setIndex}`,
        weight: set.weight,
        reps: set.reps,
        rpe: set.rpe,
      })),
    }));
}

function MobileBar({
  sets,
  tonnage,
  isPending,
}: {
  sets: number;
  tonnage: number;
  isPending: boolean;
}) {
  return (
    <div className="bg-lab-900/95 sticky bottom-[calc(env(safe-area-inset-bottom)+88px)] z-30 -mx-1 mt-2 px-1 py-2 backdrop-blur-md lg:hidden">
      <div className="bg-lab-800 ring-lab-600 flex items-center gap-3 rounded-full py-2 pl-5 pr-2 ring-1 ring-inset">
        <p className="num text-bone-300 min-w-0 flex-1 truncate text-[12px]">
          {sets} {sets === 1 ? "set" : "sets"} · {formatKg(tonnage)} kg
        </p>
        <Button
          type="submit"
          variant="primary"
          size="md"
          aria-label="Finish workout"
          disabled={isPending}
        >
          {isPending ? "Saving…" : "Finish"}
        </Button>
      </div>
    </div>
  );
}

export function SessionBuilder({ catalog }: { catalog: Exercise[] }) {
  const router = useRouter();
  const [saveState, formAction, isPending] = useActionState(
    saveWorkout,
    initialSaveState,
  );

  const [blocks, setBlocks] = useState<DraftExercise[]>([]);
  const [notes, setNotes] = useState("");
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [performedAt, setPerformedAt] = useState<string | null>(null);
  const [showErrors, setShowErrors] = useState(false);
  const [isRedo, setIsRedo] = useState(false);
  const keyRef = useRef(0);
  const pickerRef = useRef<HTMLDialogElement | null>(null);

  const catalogById = useMemo(
    () => new Map(catalog.map((entry) => [entry.id, entry])),
    [catalog],
  );
  const addedIds = useMemo(
    () => new Set(blocks.map((block) => block.exerciseId)),
    [blocks],
  );

  // Capture session start time; hydrate a delete-and-re-log handoff when asked.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("redo") === "1") {
      const handoff = readRelogHandoff();
      if (handoff) {
        setBlocks(toDraft(handoff, catalog));
        setNotes(handoff.notes.slice(0, MAX_NOTES_LENGTH));
        setPerformedAt(handoff.performedAt);
        setIsRedo(true);
        return;
      }
    }
    setPerformedAt(new Date().toISOString());
  }, [catalog]);

  useEffect(() => {
    if (saveState.status === "success") {
      clearRelogHandoff();
      router.replace(`/workouts/${saveState.workoutId}?saved=1`);
    }
  }, [saveState, router]);

  const validation = useMemo(
    () =>
      validateSession(blocks, notes, (exerciseId) =>
        exerciseNameById(catalog, exerciseId),
      ),
    [blocks, notes, catalog],
  );
  const totals = useMemo(() => computeTotals(blocks), [blocks]);
  const topSetLabel = totals.topSet
    ? `${formatKg(totals.topSet.weight)} × ${totals.topSet.reps}`
    : null;

  function nextKey(prefix: string): string {
    keyRef.current += 1;
    return `${prefix}-${keyRef.current}`;
  }

  function openPicker() {
    const dialog = pickerRef.current;
    if (!dialog) return;
    if (!dialog.open) dialog.showModal();
    requestAnimationFrame(() => {
      document.getElementById("exercise-search")?.focus();
    });
  }

  function addExercise(exerciseId: number) {
    if (addedIds.has(exerciseId)) return;
    setBlocks((current) => [
      ...current,
      {
        key: nextKey("block"),
        exerciseId,
        sets: [blankSet(nextKey("set"))],
      },
    ]);
  }

  function changeSet(
    blockKey: string,
    setKey: string,
    field: "weight" | "reps" | "rpe",
    value: string,
  ) {
    setBlocks((current) =>
      current.map((block) =>
        block.key !== blockKey
          ? block
          : {
              ...block,
              sets: block.sets.map((set) =>
                set.key !== setKey ? set : { ...set, [field]: value },
              ),
            },
      ),
    );
  }

  function addSet(blockKey: string) {
    setBlocks((current) =>
      current.map((block) => {
        if (block.key !== blockKey) return block;
        const last = block.sets[block.sets.length - 1];
        const next =
          last !== undefined
            ? {
                key: nextKey("set"),
                weight: last.weight,
                reps: last.reps,
                rpe: "",
              }
            : blankSet(nextKey("set"));
        return { ...block, sets: [...block.sets, next] };
      }),
    );
  }

  function removeSet(blockKey: string, setKey: string) {
    setBlocks((current) =>
      current.map((block) =>
        block.key !== blockKey
          ? block
          : { ...block, sets: block.sets.filter((set) => set.key !== setKey) },
      ),
    );
  }

  function removeExercise(blockKey: string) {
    setBlocks((current) => current.filter((block) => block.key !== blockKey));
  }

  function discard() {
    setBlocks([]);
    setNotes("");
    setSimulateFailure(false);
    setShowErrors(false);
    setIsRedo(false);
    setPerformedAt(new Date().toISOString());
    clearRelogHandoff();
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    setShowErrors(true);
    if (validation.summary.length > 0) {
      event.preventDefault();
    }
  }

  const payload = JSON.stringify({
    performedAt: performedAt ?? new Date().toISOString(),
    sets: buildSetsPayload(blocks),
  });

  return (
    <>
      <PageHeader
        eyebrow="Live session"
        title="Start workout"
        action={
          blocks.length > 0 ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              data-testid="add-exercise"
              onClick={openPicker}
              className="whitespace-nowrap"
            >
              <PlusIcon className="size-4" />
              Add exercise
            </Button>
          ) : undefined
        }
      />

      <div className="flex flex-col gap-4">
        {saveState.status === "success" ? (
          <div
            role="status"
            className="rounded-card bg-lab-800 ring-accent/40 flex items-center gap-3 p-4 ring-1 ring-inset"
          >
            <span
              aria-hidden="true"
              className="border-accent size-5 shrink-0 animate-spin rounded-full border-2 border-t-transparent"
            />
            <p className="text-bone-300 text-sm">
              Workout saved — taking you to the summary…
            </p>
          </div>
        ) : null}

        {saveState.status === "error" ? (
          <div
            role="alert"
            data-testid="submit-error"
            className="rounded-card bg-accent/5 ring-accent/30 flex flex-col gap-3 p-4 ring-1 ring-inset"
          >
            <span className="eyebrow text-accent">
              Couldn’t save this workout
            </span>
            <p className="text-bone-300 text-sm leading-relaxed">
              {saveState.message} Your session is still here — nothing was lost.
            </p>
            <Button
              type="submit"
              form="session-form"
              variant="primary"
              size="sm"
              disabled={isPending}
              className="self-start"
            >
              {isPending ? "Saving…" : "Retry save"}
            </Button>
          </div>
        ) : null}

        {showErrors && validation.summary.length > 0 ? (
          <div
            role="alert"
            className="rounded-card bg-lab-800 ring-accent/30 flex flex-col gap-2 p-4 ring-1 ring-inset"
          >
            <span className="eyebrow text-accent">Check your sets</span>
            <ul className="text-bone-300 flex list-disc flex-col gap-1 pl-5 text-sm leading-relaxed">
              {validation.summary.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {isRedo ? (
          <p
            data-testid="relog-notice"
            className="bg-lab-800/70 text-ash-300 ring-lab-600 rounded-2xl px-3.5 py-2.5 text-[12px] leading-relaxed ring-1 ring-inset"
          >
            Re-logging a deleted session — edit anything, then finish again.
          </p>
        ) : null}

        <form
          id="session-form"
          action={formAction}
          onSubmit={handleSubmit}
          className="flex flex-col gap-4"
        >
          <input type="hidden" name="payload" value={payload} />

          <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-6">
            <div className="flex min-w-0 flex-col gap-4">
              {blocks.length === 0 ? (
                <EmptyState
                  eyebrow="Next up"
                  title="Build your session"
                  icon={<BarbellIcon className="size-9" />}
                  body="Your session is built locally, one exercise at a time. Nothing is saved until you finish the workout."
                >
                  <Button
                    type="button"
                    variant="primary"
                    size="md"
                    data-testid="add-exercise"
                    onClick={openPicker}
                  >
                    <PlusIcon className="size-4" />
                    Add exercise
                  </Button>
                </EmptyState>
              ) : (
                blocks.map((block, index) => {
                  const exercise = catalogById.get(block.exerciseId);
                  if (!exercise) return null;
                  return (
                    <SetEditor
                      key={block.key}
                      order={index + 1}
                      exercise={exercise}
                      block={block}
                      showErrors={showErrors}
                      setErrors={validation.setErrors}
                      blockError={validation.blockErrors[block.key]}
                      onChangeSet={changeSet}
                      onAddSet={addSet}
                      onRemoveSet={removeSet}
                      onRemoveExercise={removeExercise}
                    />
                  );
                })
              )}
            </div>

            <SessionSummary
              totals={totals}
              topSetLabel={topSetLabel}
              notes={notes}
              notesError={validation.notesError}
              showErrors={showErrors}
              isPending={isPending}
              formError={
                saveState.status === "error" ? saveState.message : null
              }
              onNotesChange={setNotes}
              simulateFailure={simulateFailure}
              onSimulateChange={setSimulateFailure}
              onDiscard={discard}
            />
          </div>

          <MobileBar
            sets={totals.sets}
            tonnage={totals.tonnage}
            isPending={isPending}
          />
        </form>
      </div>

      <ExercisePicker
        dialogRef={pickerRef}
        catalog={catalog}
        addedIds={addedIds}
        onAdd={addExercise}
      />
    </>
  );
}
