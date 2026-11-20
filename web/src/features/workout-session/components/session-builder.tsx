"use client";

import { useActionState, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import type { Exercise } from "@spottr/api-client";

import { BarbellIcon, Button, PlusIcon, cn } from "~/components/ui";

import { saveWorkout } from "../actions";
import { MAX_NOTES_LENGTH } from "../model/constants";
import {
  buildSetsPayload,
  clearDraft,
  clearRelogHandoff,
  computeTotals,
  exerciseNameById,
  formatClock,
  formatKg,
  isFreshDraft,
  readDraft,
  readRelogHandoff,
  validateSession,
  writeDraft,
  type DraftExercise,
  type RelogHandoff,
  type StoredDraft,
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
  errorCount,
  showErrors,
  isPending,
  onAddExercise,
}: {
  sets: number;
  tonnage: number;
  errorCount: number;
  showErrors: boolean;
  isPending: boolean;
  onAddExercise: () => void;
}) {
  const hasErrors = showErrors && errorCount > 0;

  return (
    <div className="border-lab-700 bg-lab-900/95 sticky bottom-[calc(env(safe-area-inset-bottom)+88px)] z-30 -mx-4 mt-1 border-t px-4 py-3 backdrop-blur-md sm:-mx-6 lg:hidden">
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="secondary"
          size="icon"
          data-testid="add-exercise"
          aria-label="Add exercise"
          onClick={onAddExercise}
          className="size-11 shrink-0"
        >
          <PlusIcon className="size-4" />
        </Button>
        <p
          className={cn(
            "num min-w-0 flex-1 truncate text-[12px]",
            hasErrors ? "text-accent" : "text-bone-300",
          )}
        >
          {hasErrors
            ? `Fix ${errorCount} ${errorCount === 1 ? "field" : "fields"}`
            : `${sets} ${sets === 1 ? "set" : "sets"} · ${formatKg(tonnage)} kg`}
        </p>
        <Button
          type="submit"
          variant="primary"
          size="md"
          data-testid="finish-workout"
          aria-label="Finish workout"
          disabled={isPending}
          className="shrink-0"
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
  const [pendingDraft, setPendingDraft] = useState<StoredDraft | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const keyRef = useRef(0);
  const pickerRef = useRef<HTMLDialogElement | null>(null);
  const saveErrorRef = useRef<HTMLDivElement | null>(null);

  const catalogById = useMemo(
    () => new Map(catalog.map((entry) => [entry.id, entry])),
    [catalog],
  );
  const addedIds = useMemo(
    () => new Set(blocks.map((block) => block.exerciseId)),
    [blocks],
  );

  // Restore an explicit delete-and-re-log handoff, or offer an unfinished draft.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("redo") === "1") {
      const handoff = readRelogHandoff();
      if (handoff) {
        setBlocks(toDraft(handoff, catalog));
        setNotes(handoff.notes.slice(0, MAX_NOTES_LENGTH));
        setPerformedAt(handoff.performedAt);
        setIsRedo(true);
        clearDraft();
        setHydrated(true);
        return;
      }
    }

    const draft = readDraft();
    if (draft && draft.exercises.length > 0 && isFreshDraft(draft)) {
      setPendingDraft(draft);
    } else {
      clearDraft();
      setPerformedAt(new Date().toISOString());
    }
    setHydrated(true);
  }, [catalog]);

  useEffect(() => {
    if (saveState.status === "success") {
      clearRelogHandoff();
      clearDraft();
      router.replace(`/workouts/${saveState.workoutId}?saved=1`);
    }
  }, [saveState, router]);

  // The session clock runs while the draft has sets and the tab is open.
  useEffect(() => {
    if (!performedAt || blocks.length === 0) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [performedAt, blocks.length]);

  // Keep the active session on disk so a reload or discarded tab can resume it.
  useEffect(() => {
    if (!hydrated || pendingDraft || !performedAt) return;
    if (blocks.length === 0 && notes.length === 0) {
      clearDraft();
      return;
    }
    writeDraft({
      version: 1,
      performedAt,
      notes,
      isRedo,
      exercises: blocks.map((block) => ({
        exerciseId: block.exerciseId,
        sets: block.sets.map((set) => ({
          weight: set.weight,
          reps: set.reps,
          rpe: set.rpe,
        })),
      })),
    });
  }, [hydrated, pendingDraft, performedAt, blocks, notes, isRedo]);

  // Leave guard: browser reload/close plus every in-app link.
  const isDirty =
    hydrated && blocks.length > 0 && saveState.status !== "success";

  useEffect(() => {
    if (!isDirty) return;
    function onBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [isDirty]);

  useEffect(() => {
    if (!isDirty) return;
    function onClick(event: MouseEvent) {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }
      const anchor = (event.target as Element | null)?.closest("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) return;
      if (anchor.target === "_blank") return;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("#")) return;
      const url = new URL(href, window.location.href);
      if (
        url.pathname === window.location.pathname &&
        url.search === window.location.search
      ) {
        return;
      }
      if (
        !window.confirm("Leave this workout? Your sets stay saved as a draft.")
      ) {
        event.preventDefault();
        event.stopPropagation();
      }
    }
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, [isDirty]);

  // A failed save must be seen from the finish action, wherever it is.
  useEffect(() => {
    if (saveState.status === "error") {
      saveErrorRef.current?.scrollIntoView({
        block: "center",
        behavior: "smooth",
      });
    }
  }, [saveState.status]);

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
  const errorCount = validation.summary.length;
  const draftSetCount = pendingDraft
    ? pendingDraft.exercises.reduce(
        (total, entry) => total + entry.sets.length,
        0,
      )
    : 0;

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
    clearDraft();
  }

  function resumeDraft() {
    if (!pendingDraft) return;
    setBlocks(toDraft(pendingDraft, catalog));
    setNotes(pendingDraft.notes.slice(0, MAX_NOTES_LENGTH));
    setPerformedAt(pendingDraft.performedAt);
    setIsRedo(pendingDraft.isRedo);
    setPendingDraft(null);
  }

  function discardDraft() {
    clearDraft();
    setPendingDraft(null);
    setPerformedAt(new Date().toISOString());
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    setShowErrors(true);
    if (validation.summary.length === 0) return;

    event.preventDefault();
    window.setTimeout(() => {
      const field = document.querySelector<HTMLElement>(
        '[aria-invalid="true"]',
      );
      field?.scrollIntoView({ block: "center", behavior: "smooth" });
      field?.focus({ preventScroll: true });
    }, 0);
  }

  const payload = JSON.stringify({
    performedAt: performedAt ?? new Date().toISOString(),
    sets: buildSetsPayload(blocks),
  });
  const elapsedSeconds = performedAt
    ? Math.max(0, (now - Date.parse(performedAt)) / 1000)
    : 0;

  return (
    <>
      <header className="flex items-baseline justify-between gap-4 pb-5">
        <h1 className="display text-[22px] leading-none lg:text-[28px]">
          Workout
        </h1>
        {blocks.length > 0 ? (
          <span
            role="timer"
            aria-label="Elapsed time"
            className="num text-ash-300 text-[13px]"
          >
            {formatClock(elapsedSeconds)}
          </span>
        ) : null}
      </header>

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
            <p className="text-bone-300 text-sm">Saved. Opening the summary…</p>
          </div>
        ) : null}

        {saveState.status === "error" ? (
          <div
            ref={saveErrorRef}
            role="alert"
            data-testid="submit-error"
            className="rounded-card bg-lab-800 ring-accent/40 flex flex-col gap-3 p-4 ring-1 ring-inset"
          >
            <p className="text-bone-300 text-sm leading-relaxed">
              {saveState.message}
            </p>
            <Button
              type="submit"
              form="session-form"
              variant="secondary"
              size="sm"
              disabled={isPending}
              className="self-start"
            >
              {isPending ? "Saving…" : "Try again"}
            </Button>
          </div>
        ) : null}

        {isRedo ? (
          <p
            data-testid="relog-notice"
            className="bg-lab-800/70 text-ash-300 ring-lab-600 rounded-2xl px-3.5 py-2.5 text-[12px] leading-relaxed ring-1 ring-inset"
          >
            Sets prefilled from the deleted workout. Fix anything, then finish.
          </p>
        ) : null}

        {pendingDraft ? (
          <div
            role="status"
            data-testid="resume-draft"
            className="rounded-panel bg-lab-800 ring-lab-600 flex flex-col gap-3 p-4 ring-1 ring-inset sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex min-w-0 flex-col gap-1">
              <h2 className="display text-[16px] leading-none">
                Unfinished session
              </h2>
              <p className="num text-ash-300 text-[12px] leading-relaxed">
                {pendingDraft.exercises.length}{" "}
                {pendingDraft.exercises.length === 1 ? "exercise" : "exercises"}{" "}
                · {draftSetCount} {draftSetCount === 1 ? "set" : "sets"}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                data-testid="discard-draft"
                onClick={discardDraft}
              >
                Discard
              </Button>
              <Button
                type="button"
                variant="primary"
                size="sm"
                data-testid="resume-draft-confirm"
                onClick={resumeDraft}
              >
                Resume
              </Button>
            </div>
          </div>
        ) : null}

        <form
          id="session-form"
          action={formAction}
          onSubmit={handleSubmit}
          className="flex flex-col gap-4"
        >
          <input type="hidden" name="payload" value={payload} />

          <div
            className={cn(
              "grid items-start gap-4",
              blocks.length > 0 &&
                "lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-6",
            )}
          >
            <div className="min-w-0">
              {pendingDraft ? (
                <div aria-hidden="true" />
              ) : !hydrated ? (
                <div className="h-24" aria-hidden="true" />
              ) : blocks.length === 0 ? (
                <div className="rounded-panel bg-lab-800 flex flex-col items-start gap-4 px-5 py-6">
                  <BarbellIcon className="text-accent size-7" />
                  <div className="flex flex-col gap-1.5">
                    <h2 className="display text-[20px] leading-none">
                      No exercises yet
                    </h2>
                    <p className="text-bone-300 max-w-prose text-sm leading-relaxed">
                      Add a lift, then log each set as you do it.
                    </p>
                  </div>
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
                </div>
              ) : (
                <div className="rounded-panel bg-lab-800 overflow-hidden">
                  <div
                    aria-hidden="true"
                    className="num text-ash-400 grid grid-cols-[1.25rem_1fr_1fr_1fr_2.5rem] gap-x-2 px-4 pb-1 pt-3 text-[11px] uppercase tracking-[0.08em] sm:px-5"
                  >
                    <span className="text-center">#</span>
                    <span className="text-right">kg</span>
                    <span className="text-right">reps</span>
                    <span className="text-right">RPE</span>
                    <span />
                  </div>
                  <div className="divide-lab-700 divide-y">
                    {blocks.map((block) => {
                      const exercise = catalogById.get(block.exerciseId);
                      if (!exercise) return null;
                      return (
                        <SetEditor
                          key={block.key}
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
                    })}
                    <button
                      type="button"
                      data-testid="add-exercise"
                      onClick={openPicker}
                      className="text-ash-300 hover:bg-lab-700/40 hover:text-bone-100 flex h-14 w-full items-center gap-2 px-4 text-[13px] transition-colors sm:px-5"
                    >
                      <PlusIcon className="size-4" />
                      Add exercise
                    </button>
                  </div>
                </div>
              )}
            </div>

            {blocks.length > 0 ? (
              <SessionSummary
                totals={totals}
                topSetLabel={topSetLabel}
                notes={notes}
                notesError={validation.notesError}
                showErrors={showErrors}
                errorCount={errorCount}
                isPending={isPending}
                onNotesChange={setNotes}
                simulateFailure={simulateFailure}
                onSimulateChange={setSimulateFailure}
                onDiscard={discard}
              />
            ) : null}
          </div>

          {blocks.length > 0 ? (
            <MobileBar
              sets={totals.sets}
              tonnage={totals.tonnage}
              errorCount={errorCount}
              showErrors={showErrors}
              isPending={isPending}
              onAddExercise={openPicker}
            />
          ) : null}
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
