"use client";

import { useActionState, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import type { Exercise } from "@spottr/api-client";

import {
  BarbellIcon,
  Button,
  DiscardIcon,
  PlusIcon,
  cn,
} from "~/components/ui";

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
  type DraftSet,
  type RelogHandoff,
  type StoredDraft,
} from "../model/session";
import { initialSaveState } from "../model/state";
import { ExercisePicker } from "./exercise-picker";
import { SetEditor } from "./set-editor";
import { SessionSummary } from "./session-summary";

function blankSet(key: string) {
  return { key, weight: "", reps: "", rpe: "", completed: false };
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
        completed: set.completed ?? true,
      })),
    }));
}

function MobileBar({
  sets,
  totalSets,
  tonnage,
  errorCount,
  showErrors,
  canFinish,
  confirmDiscard,
  isPending,
  onAddExercise,
  onDiscard,
}: {
  sets: number;
  totalSets: number;
  tonnage: number;
  errorCount: number;
  showErrors: boolean;
  canFinish: boolean;
  confirmDiscard: boolean;
  isPending: boolean;
  onAddExercise: () => void;
  onDiscard: () => void;
}) {
  const hasErrors = showErrors && errorCount > 0;

  return (
    <div className="border-lab-700 bg-lab-900/95 sticky bottom-[calc(env(safe-area-inset-bottom)+88px)] z-30 -mx-4 mt-1 border-t px-4 py-3 backdrop-blur-md sm:-mx-6 lg:hidden">
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          data-testid="discard-session-mobile"
          aria-label={
            confirmDiscard ? "Tap again to discard" : "Discard session"
          }
          title={confirmDiscard ? "Tap again to discard" : "Discard session"}
          onClick={onDiscard}
          className={cn("size-11 shrink-0", confirmDiscard && "text-accent")}
        >
          <DiscardIcon className="size-4" />
        </Button>
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
            : !canFinish
              ? "Check a set to finish"
              : `${sets}${sets === totalSets ? "" : `/${totalSets}`} ${sets === 1 && totalSets === 1 ? "set" : "sets"} · ${formatKg(tonnage)} kg`}
        </p>
        <Button
          type="submit"
          variant="primary"
          size="md"
          data-testid="finish-workout"
          aria-label="Finish workout"
          disabled={isPending || !canFinish}
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
  const [removed, setRemoved] = useState<
    | { kind: "exercise"; block: DraftExercise; index: number; name: string }
    | {
        kind: "set";
        blockKey: string;
        set: DraftSet;
        index: number;
        name: string;
      }
    | null
  >(null);
  const [hydrated, setHydrated] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
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
    }
    setHydrated(true);
  }, [catalog]);

  useEffect(() => {
    if (saveState.status === "success") {
      clearRelogHandoff();
      clearDraft();
      setRemoved(null);
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
          completed: set.completed,
        })),
      })),
    });
  }, [hydrated, pendingDraft, performedAt, blocks, notes, isRedo]);

  useEffect(() => {
    if (!removed) return;
    const id = window.setTimeout(() => setRemoved(null), 6000);
    return () => window.clearTimeout(id);
  }, [removed]);

  useEffect(() => {
    if (!confirmDiscard) return;
    const id = window.setTimeout(() => setConfirmDiscard(false), 4000);
    return () => window.clearTimeout(id);
  }, [confirmDiscard]);

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
  const totalSets = blocks.reduce(
    (total, block) => total + block.sets.length,
    0,
  );
  const completedSets = blocks.reduce(
    (total, block) => total + block.sets.filter((set) => set.completed).length,
    0,
  );
  const canFinish = completedSets > 0;
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
    setRemoved(null);
    setPerformedAt((current) => current ?? new Date().toISOString());
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
    const block = blocks.find((entry) => entry.key === blockKey);
    const last = block?.sets[block.sets.length - 1];
    const next = blankSet(nextKey("set"));
    if (last) next.weight = last.weight;
    setBlocks((current) =>
      current.map((entry) =>
        entry.key !== blockKey
          ? entry
          : { ...entry, sets: [...entry.sets, next] },
      ),
    );
    // The new row is a plan: weight only, reps blank, not counted.
    window.setTimeout(() => {
      document.getElementById(`${blockKey}-${next.key}-weight`)?.focus();
    }, 0);
  }

  function toggleSet(blockKey: string, setKey: string) {
    setBlocks((current) =>
      current.map((block) =>
        block.key !== blockKey
          ? block
          : {
              ...block,
              sets: block.sets.map((set) =>
                set.key !== setKey
                  ? set
                  : { ...set, completed: !set.completed },
              ),
            },
      ),
    );
  }

  function removeSet(blockKey: string, setKey: string) {
    const block = blocks.find((entry) => entry.key === blockKey);
    const index = block?.sets.findIndex((set) => set.key === setKey) ?? -1;
    const set = block?.sets[index];
    if (!block || index === -1 || !set) return;
    const exercise = catalogById.get(block.exerciseId);
    setRemoved({
      kind: "set",
      blockKey,
      set,
      index,
      name: exercise?.name ?? "Exercise",
    });
    setBlocks((current) =>
      current.map((entry) =>
        entry.key !== blockKey
          ? entry
          : {
              ...entry,
              sets: entry.sets.filter((item) => item.key !== setKey),
            },
      ),
    );
  }

  function removeExercise(blockKey: string) {
    const index = blocks.findIndex((block) => block.key === blockKey);
    const block = blocks[index];
    if (index === -1 || !block) return;
    const exercise = catalogById.get(block.exerciseId);
    setRemoved({
      kind: "exercise",
      block,
      index,
      name: exercise?.name ?? "Exercise",
    });
    setBlocks((current) => current.filter((entry) => entry.key !== blockKey));
  }

  function undoRemove() {
    if (!removed) return;
    if (removed.kind === "exercise") {
      setBlocks((current) => {
        if (current.some((block) => block.key === removed.block.key)) {
          return current;
        }
        const next = [...current];
        next.splice(Math.min(removed.index, next.length), 0, removed.block);
        return next;
      });
    } else {
      setBlocks((current) =>
        current.map((block) => {
          if (block.key !== removed.blockKey) return block;
          if (block.sets.some((set) => set.key === removed.set.key)) {
            return block;
          }
          const next = [...block.sets];
          next.splice(Math.min(removed.index, next.length), 0, removed.set);
          return { ...block, sets: next };
        }),
      );
    }
    setRemoved(null);
  }

  function discard() {
    setBlocks([]);
    setNotes("");
    setSimulateFailure(false);
    setShowErrors(false);
    setIsRedo(false);
    setRemoved(null);
    setConfirmDiscard(false);
    setPerformedAt(null);
    clearRelogHandoff();
    clearDraft();
  }

  function requestDiscard() {
    if (!confirmDiscard) {
      setConfirmDiscard(true);
      return;
    }
    setConfirmDiscard(false);
    discard();
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
    setRemoved(null);
    setPerformedAt(null);
  }

  function handleFormKeyDown(event: React.KeyboardEvent<HTMLFormElement>) {
    if (event.key !== "Enter") return;
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (
      target.tagName === "TEXTAREA" ||
      target.tagName === "BUTTON" ||
      target.tagName === "SELECT"
    ) {
      return;
    }
    // A valid form would otherwise submit and save mid-session.
    event.preventDefault();
    const fields = Array.from(
      event.currentTarget.querySelectorAll<HTMLElement>(
        'input:not([type="hidden"])',
      ),
    );
    const next = fields[fields.indexOf(target) + 1];
    if (next) next.focus();
    else target.blur();
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
            className="num bg-lab-800 text-bone-100 rounded-full px-2.5 py-1 text-[14px] leading-none"
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

        {removed ? (
          <div
            role="status"
            data-testid="removed-item"
            className="bg-lab-800 ring-lab-600 fixed inset-x-4 top-4 z-40 flex items-center justify-between gap-3 rounded-2xl px-4 py-2.5 shadow-[0_12px_32px_rgba(0,0,0,0.45)] ring-1 ring-inset sm:inset-x-auto sm:right-6 sm:w-[340px]"
          >
            <p className="text-ash-300 text-[12px]">
              {removed.kind === "exercise"
                ? `Removed ${removed.name}.`
                : `Removed set ${removed.index + 1} of ${removed.name}.`}
            </p>
            <Button
              type="button"
              variant="ghost"
              size="md"
              data-testid="undo-remove"
              onClick={undoRemove}
              className="text-bone-100"
            >
              Undo
            </Button>
          </div>
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
          onKeyDown={handleFormKeyDown}
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
                <div className="rounded-panel bg-lab-800">
                  <div
                    aria-hidden="true"
                    className="num text-bone-300 border-lab-600 bg-lab-800 rounded-t-panel sticky top-0 z-10 grid grid-cols-[2.75rem_1fr_1fr_1fr_2.75rem] gap-x-2 border-b px-4 pb-1 pt-3 text-[12px] uppercase tracking-[0.08em] sm:px-5"
                  >
                    <span className="text-center">Set</span>
                    <span className="text-right">kg</span>
                    <span className="text-right">reps</span>
                    <span className="text-right">RPE</span>
                    <span />
                  </div>
                  <div className="divide-lab-700 rounded-b-panel divide-y overflow-hidden">
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
                          onToggleSet={toggleSet}
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
                totalSets={totalSets}
                completedSets={completedSets}
                canFinish={canFinish}
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
              sets={completedSets}
              totalSets={totalSets}
              tonnage={totals.tonnage}
              errorCount={errorCount}
              showErrors={showErrors}
              canFinish={canFinish}
              confirmDiscard={confirmDiscard}
              isPending={isPending}
              onAddExercise={openPicker}
              onDiscard={requestDiscard}
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
