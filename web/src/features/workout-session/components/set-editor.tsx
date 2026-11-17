import type { Exercise } from "@spottr/api-client";

import { Button, CloseIcon, PlusIcon, TrashIcon, cn } from "~/components/ui";

import {
  formatCategory,
  type DraftExercise,
  type SetFieldErrors,
} from "../model/session";

interface SetEditorProps {
  order: number;
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

const inputClasses =
  "num bg-lab-700 h-12 w-full rounded-2xl px-3 text-center text-[16px] shadow-[inset_0_0_0_1px_var(--color-lab-600)] focus:shadow-[inset_0_0_0_1.5px_var(--color-accent)] focus:outline-none";

const invalidClasses = "shadow-[inset_0_0_0_1.5px_var(--color-accent)]";

interface NumberFieldProps {
  id: string;
  label: string;
  testid: "set-weight" | "set-reps" | "set-rpe";
  value: string;
  error?: string;
  showErrors: boolean;
  inputMode: "decimal" | "numeric";
  placeholder: string;
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
  placeholder,
  onChange,
}: NumberFieldProps) {
  const invalid = showErrors && error !== undefined;
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <input
        id={id}
        data-testid={testid}
        value={value}
        inputMode={inputMode}
        placeholder={placeholder}
        autoComplete="off"
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={invalid || undefined}
        aria-describedby={invalid ? `${id}-error` : undefined}
        className={cn(inputClasses, invalid && invalidClasses)}
      />
      {invalid ? (
        <span
          id={`${id}-error`}
          className="text-accent text-[11px] leading-tight"
        >
          {error}
        </span>
      ) : null}
    </div>
  );
}

/** One exercise card: header, editable set rows, add-set. Always editable. */
export function SetEditor({
  order,
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
  const orderLabel = String(order).padStart(2, "0");

  return (
    <section
      data-testid="exercise-card"
      data-exercise-name={exercise.name}
      aria-label={exercise.name}
      className="rounded-panel bg-lab-800 flex flex-col gap-4 p-[18px]"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-baseline gap-3">
          <span className="num text-accent text-[13px]">{orderLabel}</span>
          <div className="flex min-w-0 flex-col gap-1">
            <h3 className="display text-[17px] leading-tight">
              {exercise.name}
            </h3>
            <span className="text-ash-300 text-[12px] leading-tight">
              {formatCategory(exercise.category)}
              {exercise.is_compound ? " · compound" : ""}
            </span>
          </div>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          data-testid="remove-exercise"
          aria-label={`Remove ${exercise.name}`}
          title={`Remove ${exercise.name}`}
          onClick={() => onRemoveExercise(block.key)}
          className="size-9 shrink-0"
        >
          <CloseIcon className="size-4" />
        </Button>
      </div>

      <div
        aria-hidden="true"
        className="num text-ash-500 grid grid-cols-[2rem_1fr_1fr_1fr_2.25rem] items-center gap-2 px-0 text-[10px] uppercase tracking-[0.12em]"
      >
        <span className="text-center">Set</span>
        <span className="text-center">Load kg</span>
        <span className="text-center">Reps</span>
        <span className="text-center">RPE</span>
        <span />
      </div>

      <ul className="flex flex-col gap-2">
        {block.sets.map((set, index) => {
          const errors = setErrors[set.key] ?? {};
          return (
            <li
              key={set.key}
              data-testid="set-row"
              className="grid grid-cols-[2rem_1fr_1fr_1fr_2.25rem] items-start gap-2"
            >
              <span className="num text-ash-300 flex h-12 items-center justify-center text-[13px]">
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
                placeholder="80"
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
                placeholder="5"
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
                placeholder="–"
                onChange={(value) =>
                  onChangeSet(block.key, set.key, "rpe", value)
                }
              />
              <Button
                type="button"
                variant="ghost"
                data-testid="remove-set"
                aria-label={`Remove ${exercise.name} set ${index + 1}`}
                title={`Remove set ${index + 1}`}
                onClick={() => onRemoveSet(block.key, set.key)}
                className="size-9 justify-self-center p-0"
              >
                <TrashIcon className="size-4" />
              </Button>
            </li>
          );
        })}
      </ul>

      {showErrors && blockError ? (
        <p role="alert" className="text-accent text-[12px] leading-relaxed">
          {blockError}
        </p>
      ) : null}

      <Button
        type="button"
        variant="secondary"
        size="md"
        fullWidth
        data-testid="add-set"
        onClick={() => onAddSet(block.key)}
      >
        <PlusIcon className="size-4" />
        Add set
      </Button>
    </section>
  );
}
