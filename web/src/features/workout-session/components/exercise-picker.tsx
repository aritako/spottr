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
      className="bg-lab-800 text-bone-100 rounded-panel m-auto max-h-[80dvh] w-[min(560px,calc(100vw-2rem))] p-0 backdrop:bg-black/70 backdrop:backdrop-blur-sm"
    >
      <div className="flex max-h-[80dvh] flex-col">
        <div className="flex items-start justify-between gap-4 p-[18px] pb-0">
          <div className="flex flex-col gap-1.5">
            <span className="eyebrow">Exercise catalog</span>
            <h2 className="display text-xl leading-none">Add exercise</h2>
            <p className="num text-ash-400 text-[11px]">
              {catalog.length} exercises
            </p>
          </div>
          <Button
            type="button"
            variant="secondary"
            size="icon"
            aria-label="Close picker"
            onClick={close}
            className="shrink-0"
          >
            <CloseIcon className="size-4" />
          </Button>
        </div>

        <div className="p-[18px]">
          <label htmlFor="exercise-search" className="sr-only">
            Search exercises
          </label>
          <div className="bg-lab-700 flex items-center gap-2 rounded-full px-4 shadow-[inset_0_0_0_1px_var(--color-lab-600)] focus-within:shadow-[inset_0_0_0_1.5px_var(--color-accent)]">
            <SearchIcon className="text-ash-500 size-4 shrink-0" />
            <input
              id="exercise-search"
              data-testid="exercise-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search exercises"
              autoComplete="off"
              className="placeholder:text-ash-500 h-11 min-w-0 flex-1 bg-transparent text-[15px] focus:outline-none"
            />
          </div>
        </div>

        <ul className="flex flex-col gap-1 overflow-y-auto px-3 pb-3">
          {filtered.map((entry) => {
            const added = addedIds.has(entry.id);
            return (
              <li
                key={entry.id}
                className="hover:bg-lab-700/60 flex items-center gap-3 rounded-2xl px-3 py-2.5 transition-colors"
              >
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="truncate text-[15px] font-medium">
                    {entry.name}
                  </span>
                  <span className="text-ash-300 text-[12px]">
                    {formatCategory(entry.category)}
                    {entry.is_compound ? " · compound" : ""}
                  </span>
                </div>
                {added ? (
                  <span
                    data-testid="exercise-option"
                    data-exercise-name={entry.name}
                    aria-disabled="true"
                    className="text-ash-300 inline-flex h-9 items-center gap-1.5 px-3 text-[12px] font-semibold"
                  >
                    <CheckIcon className="text-accent size-4" />
                    Added
                  </span>
                ) : (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    data-testid="exercise-option"
                    data-exercise-name={entry.name}
                    onClick={() => onAdd(entry.id)}
                    aria-label={`Add ${entry.name}`}
                  >
                    <PlusIcon className="size-3.5" />
                    Add
                  </Button>
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

        <div className="border-lab-600 flex justify-end border-t p-3">
          <Button
            type="button"
            variant="primary"
            size="md"
            data-testid="picker-done"
            onClick={close}
            className="w-full sm:w-auto"
          >
            Done
          </Button>
        </div>
      </div>
    </dialog>
  );
}
