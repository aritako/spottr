import { useState, type RefObject } from "react";

import type { Exercise } from "@spottr/api-client";

import {
  Button,
  CheckIcon,
  CloseIcon,
  PlusIcon,
  SearchIcon,
} from "~/components/ui";

import { formatCategory } from "../model/session";

interface ExercisePickerProps {
  dialogRef: RefObject<HTMLDialogElement | null>;
  catalog: Exercise[];
  addedIds: Set<number>;
  onAdd: (exerciseId: number) => void;
}

/** Modal exercise picker over the loaded catalog. Stays open for multi-add. */
export function ExercisePicker({
  dialogRef,
  catalog,
  addedIds,
  onAdd,
}: ExercisePickerProps) {
  const [query, setQuery] = useState("");

  const needle = query.trim().toLowerCase();
  const filtered =
    needle === ""
      ? catalog
      : catalog.filter((entry) => entry.name.toLowerCase().includes(needle));

  function close() {
    dialogRef.current?.close();
  }

  return (
    <dialog
      ref={dialogRef}
      data-testid="exercise-picker"
      aria-label="Add exercise"
      onClose={() => setQuery("")}
      onClick={(event) => {
        if (event.target === dialogRef.current) close();
      }}
      className="bg-lab-800 text-bone-100 rounded-panel m-auto max-h-[80dvh] w-[min(520px,calc(100vw-2rem))] p-0 backdrop:bg-black/70 backdrop:backdrop-blur-sm"
    >
      <div className="flex max-h-[80dvh] flex-col">
        <div className="flex items-center justify-between gap-4 p-4 pb-0 sm:p-5 sm:pb-0">
          <h2 className="display text-lg leading-none">Add exercise</h2>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="Close picker"
            onClick={close}
            className="-mr-2 size-10 shrink-0"
          >
            <CloseIcon className="size-4" />
          </Button>
        </div>

        <div className="p-4 sm:p-5">
          <label htmlFor="exercise-search" className="sr-only">
            Search exercises
          </label>
          <div className="bg-lab-700 flex items-center gap-2 rounded-full px-4 shadow-[inset_0_0_0_1px_var(--color-lab-600)] focus-within:shadow-[inset_0_0_0_1.5px_var(--color-accent)]">
            <SearchIcon className="text-ash-400 size-4 shrink-0" />
            <input
              id="exercise-search"
              data-testid="exercise-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search exercises"
              autoComplete="off"
              className="placeholder:text-ash-400 h-11 min-w-0 flex-1 bg-transparent text-[15px] focus:outline-none"
            />
          </div>
        </div>

        <ul className="flex flex-col overflow-y-auto px-2 pb-2">
          {filtered.map((entry) => {
            const added = addedIds.has(entry.id);
            const label = (
              <span className="flex min-w-0 flex-1 flex-col gap-0.5 text-left">
                <span className="truncate text-[15px]">{entry.name}</span>
                <span className="text-ash-400 text-[11px]">
                  {formatCategory(entry.category)}
                </span>
              </span>
            );

            return (
              <li key={entry.id}>
                {added ? (
                  <div
                    data-testid="exercise-option"
                    data-exercise-name={entry.name}
                    aria-disabled="true"
                    className="flex h-14 items-center gap-3 rounded-xl px-2.5"
                  >
                    {label}
                    <span className="text-ash-400 inline-flex items-center gap-1.5 text-[12px]">
                      <CheckIcon className="text-accent size-4" />
                      Added
                    </span>
                  </div>
                ) : (
                  <button
                    type="button"
                    data-testid="exercise-option"
                    data-exercise-name={entry.name}
                    onClick={() => onAdd(entry.id)}
                    aria-label={`Add ${entry.name}`}
                    className="hover:bg-lab-700/60 group flex h-14 w-full items-center gap-3 rounded-xl px-2.5 transition-colors"
                  >
                    {label}
                    <PlusIcon className="text-ash-400 group-hover:text-bone-100 size-4 shrink-0 transition-colors" />
                  </button>
                )}
              </li>
            );
          })}
          {filtered.length === 0 ? (
            <li className="text-ash-300 px-3 py-8 text-center text-sm">
              No exercises match “{query.trim()}”.
            </li>
          ) : null}
        </ul>

        <div className="border-lab-700 flex items-center justify-between gap-3 border-t p-3 sm:p-4">
          <span className="num text-ash-400 pl-2 text-[11px]">
            {addedIds.size} added
          </span>
          <Button
            type="button"
            variant="primary"
            size="md"
            data-testid="picker-done"
            onClick={close}
          >
            Done
          </Button>
        </div>
      </div>
    </dialog>
  );
}
