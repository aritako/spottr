import type { Exercise } from "@spottr/api-client";

import { Button, CloseIcon, PlusIcon, TrashIcon, cn } from "~/components/ui";

import type { DraftExercise, SetFieldErrors } from "../model/session";

interface SetEditorProps {
  exercise: Exercise;
  block: DraftExercise;
  showErrors: boolean;
  setErrors: Record<string, SetFieldErrors>;
  blockError?: string;
  onChangeSet: (
    blockKey: string,
    setKey: string,
    field: "weight" | "reps" | "rpe",
    value: string,
  ) => void;
  onAddSet: (blockKey: string) => void;
  onRemoveSet: (blockKey: string, setKey: string) => void;
  onRemoveExercise: (blockKey: string) => void;
}

const fieldClasses =
  "num h-11 w-full min-w-0 rounded-md bg-transparent text-right text-[18px] leading-none " +
  "text-bone-100 shadow-[inset_0_-1px_0_0_var(--color-lab-600)] " +
  "transition-[box-shadow,background-color] duration-150 " +
  "placeholder:text-ash-400 " +
  "hover:shadow-[inset_0_-1px_0_0_var(--color-lab-500)] " +
  "focus:bg-lab-700/45 focus:shadow-[inset_0_-2px_0_0_var(--color-accent)]";

const invalidClasses =
  "bg-accent/5 shadow-[inset_0_-2px_0_0_var(--color-accent)] hover:shadow-[inset_0_-2px_0_0_var(--color-accent)]";

interface NumberFieldProps {
  id: string;
  label: string;
  testid: "set-weight" | "set-reps" | "set-rpe";
  value: string;
  error?: string;
  showErrors: boolean;
  inputMode: "decimal" | "numeric";
  onChange: (value: string) => void;
}

function NumberField({
  id,
  label,
  testid,
  value,
  error,
  showErrors,
  inputMode,
  onChange,
}: NumberFieldProps) {
  const invalid = showErrors && error !== undefined;
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <input
        id={id}
        data-testid={testid}
        value={value}
        inputMode={inputMode}
        enterKeyHint="next"
        placeholder="–"
        autoComplete="off"
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={invalid || undefined}
        aria-describedby={invalid ? `${id}-error` : undefined}
        className={cn(fieldClasses, invalid && invalidClasses)}
      />
      {invalid ? (
        <span
          id={`${id}-error`}
          className="text-accent text-right text-[12px] leading-tight"
        >
          {error}
        </span>
      ) : null}
    </div>
  );
}

/** One exercise block: a ruled set list on the shared session sheet. */
export function SetEditor({
  exercise,
  block,
  showErrors,
  setErrors,
  blockError,
  onChangeSet,
  onAddSet,
  onRemoveSet,
  onRemoveExercise,
}: SetEditorProps) {
  return (
    <section
      data-testid="exercise-card"
      data-exercise-name={exercise.name}
      aria-label={exercise.name}
      className="flex flex-col px-4 py-4 sm:px-5"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 className="display min-w-0 truncate text-[16px] leading-none">
          {exercise.name}
        </h2>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          data-testid="remove-exercise"
          aria-label={`Remove ${exercise.name}`}
          title={`Remove ${exercise.name}`}
          onClick={() => onRemoveExercise(block.key)}
          className="-mr-2 size-10 shrink-0"
        >
          <CloseIcon className="size-4" />
        </Button>
      </div>

      <ul className="mt-2 flex flex-col gap-1">
        {block.sets.map((set, index) => {
          const errors = setErrors[set.key] ?? {};
          return (
            <li
              key={set.key}
              data-testid="set-row"
              className="group grid grid-cols-[1.25rem_1fr_1fr_1fr_2.75rem] items-start gap-x-2"
            >
              <span className="num text-ash-400 flex h-11 items-center justify-center text-[11px]">
                {index + 1}
              </span>
              <NumberField
                id={`${block.key}-${set.key}-weight`}
                label={`${exercise.name} set ${index + 1} weight in kilograms`}
                testid="set-weight"
                value={set.weight}
                error={errors.weight}
                showErrors={showErrors}
                inputMode="decimal"
                onChange={(value) =>
                  onChangeSet(block.key, set.key, "weight", value)
                }
              />
              <NumberField
                id={`${block.key}-${set.key}-reps`}
                label={`${exercise.name} set ${index + 1} reps`}
                testid="set-reps"
                value={set.reps}
                error={errors.reps}
                showErrors={showErrors}
                inputMode="numeric"
                onChange={(value) =>
                  onChangeSet(block.key, set.key, "reps", value)
                }
              />
              <NumberField
                id={`${block.key}-${set.key}-rpe`}
                label={`${exercise.name} set ${index + 1} RPE, optional`}
                testid="set-rpe"
                value={set.rpe}
                error={errors.rpe}
                showErrors={showErrors}
                inputMode="decimal"
                onChange={(value) =>
                  onChangeSet(block.key, set.key, "rpe", value)
                }
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                data-testid="remove-set"
                aria-label={`Remove ${exercise.name} set ${index + 1}`}
                title={
                  block.sets.length === 1
                    ? "A block needs at least one set"
                    : `Remove set ${index + 1}`
                }
                disabled={block.sets.length === 1}
                onClick={() => onRemoveSet(block.key, set.key)}
                className="shrink-0 transition-opacity lg:opacity-0 lg:group-focus-within:opacity-100 lg:group-hover:opacity-100"
              >
                <TrashIcon className="text-ash-500 size-4" />
              </Button>
            </li>
          );
        })}
      </ul>

      {showErrors && blockError ? (
        <p
          role="alert"
          className="text-accent mt-1 text-[12px] leading-relaxed"
        >
          {blockError}
        </p>
      ) : null}

      <button
        type="button"
        data-testid="add-set"
        onClick={() => onAddSet(block.key)}
        className="text-ash-300 hover:text-bone-100 -ml-1 mt-1 inline-flex h-11 items-center gap-1.5 self-start rounded-lg px-1 text-[13px] transition-colors"
      >
        <PlusIcon className="size-3.5" />
        Add set
      </button>
    </section>
  );
}
