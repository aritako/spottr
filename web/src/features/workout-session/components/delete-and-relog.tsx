"use client";

import { useActionState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

import { Button } from "~/components/ui";

import { deleteWorkout } from "../actions";
import { writeRelogHandoff, type RelogHandoff } from "../model/session";
import { initialDeleteState } from "../model/state";

/** Correction path: confirm delete, stash sets in sessionStorage, re-log. */
export function DeleteAndRelog({
  workoutId,
  handoff,
}: {
  workoutId: number;
  handoff: RelogHandoff;
}) {
  const router = useRouter();
  const [state, formAction, isPending] = useActionState(
    deleteWorkout,
    initialDeleteState,
  );
  const dialogRef = useRef<HTMLDialogElement | null>(null);

  useEffect(() => {
    if (state.status === "success") {
      router.push("/workouts/start?redo=1");
    }
  }, [state, router]);

  function open() {
    if (!dialogRef.current?.open) dialogRef.current?.showModal();
  }

  function close() {
    dialogRef.current?.close();
  }

  return (
    <>
      <Button
        type="button"
        variant="secondary"
        size="md"
        data-testid="delete-and-relog"
        onClick={open}
        className="self-start"
      >
        Delete &amp; re-log
      </Button>

      <dialog
        ref={dialogRef}
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
        onClick={(event) => {
          if (event.target === dialogRef.current) close();
        }}
        className="bg-lab-800 text-bone-100 rounded-panel m-auto w-[min(480px,calc(100vw-2rem))] p-0 backdrop:bg-black/70 backdrop:backdrop-blur-sm"
      >
        <form
          action={formAction}
          onSubmit={() => writeRelogHandoff(handoff)}
          className="flex flex-col gap-4 p-5 sm:p-6"
        >
          <input type="hidden" name="workout_id" value={workoutId} />
          <div className="flex flex-col gap-1.5">
            <h2
              id="delete-dialog-title"
              className="display text-xl leading-none"
            >
              Delete and re-log?
            </h2>
            <p
              id="delete-dialog-description"
              className="text-bone-300 text-sm leading-relaxed"
            >
              This permanently deletes the saved workout. Your sets reopen in
              the builder so you can fix them and save again.
            </p>
          </div>

          {state.status === "error" ? (
            <p
              role="alert"
              data-testid="correction-error"
              className="text-accent text-[13px] leading-relaxed"
            >
              {state.message}
            </p>
          ) : null}

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="ghost"
              size="md"
              data-testid="cancel-delete"
              onClick={close}
              disabled={isPending}
              className="w-full sm:w-auto"
            >
              Keep workout
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              data-testid="confirm-delete"
              disabled={isPending}
              className="w-full sm:w-auto"
            >
              {isPending ? "Deleting…" : "Delete & re-log"}
            </Button>
          </div>
        </form>
      </dialog>
    </>
  );
}
