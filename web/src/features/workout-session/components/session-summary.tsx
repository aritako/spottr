import { Button, PlateLoader, platesForWeight } from "~/components/ui";

import { MAX_NOTES_LENGTH } from "../model/constants";
import { formatKg, type SessionTotals } from "../model/session";

interface SessionSummaryProps {
  totals: SessionTotals;
  topSetLabel: string | null;
  notes: string;
  notesError?: string;
  showErrors: boolean;
  isPending: boolean;
  formError: string | null;
  onNotesChange: (value: string) => void;
  simulateFailure: boolean;
  onSimulateChange: (value: boolean) => void;
  onDiscard: () => void;
}

function Stat({
  label,
  testid,
  children,
}: {
  label: string;
  testid: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="eyebrow">{label}</span>
      <span data-testid={testid} className="num text-[22px] leading-none">
        {children}
      </span>
    </div>
  );
}

/** Sticky sidebar: totals, plate loader, notes, finish, prototype controls. */
export function SessionSummary({
  totals,
  topSetLabel,
  notes,
  notesError,
  showErrors,
  isPending,
  formError,
  onNotesChange,
  simulateFailure,
  onSimulateChange,
  onDiscard,
}: SessionSummaryProps) {
  const topWeight = totals.topSet?.weight ?? 0;
  const plates = platesForWeight(topWeight);
  const caption =
    plates.length > 0
      ? `20 + 2 × (${plates.join(" · ")})`
      : "Empty bar · add a top set";

  return (
    <aside aria-label="Session summary" className="lg:sticky lg:top-8">
      <div className="rounded-panel bg-lab-800 flex flex-col gap-5 p-[18px]">
        <div className="flex flex-col gap-1">
          <span className="eyebrow">Session total</span>
          <p className="text-ash-300 text-[12px] leading-relaxed">
            All loads in kilograms. One POST saves the whole session.
          </p>
        </div>

        <dl className="grid grid-cols-2 gap-x-4 gap-y-5">
          <Stat label="Exercises" testid="session-total-exercises">
            {totals.exercises}
          </Stat>
          <Stat label="Working sets" testid="session-total-sets">
            {totals.sets}
          </Stat>
          <Stat label="Tonnage" testid="session-tonnage">
            {formatKg(totals.tonnage)}
            <span className="text-ash-300 text-[12px]"> kg</span>
          </Stat>
          <Stat label="Top set" testid="session-top-set">
            {topSetLabel ?? "—"}
          </Stat>
        </dl>

        <figure className="flex flex-col gap-1.5">
          <PlateLoader
            weightKg={topWeight}
            label={
              totals.topSet
                ? `Barbell loaded to ${formatKg(topWeight)} kilograms: 20 kilogram bar plus ${plates.join(", ")} kilograms per side.`
                : "Empty barbell, no top set logged yet."
            }
          />
          <figcaption className="num text-ash-500 text-center text-[10px]">
            {caption}
          </figcaption>
        </figure>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="notes-input" className="eyebrow">
            Session notes
          </label>
          <textarea
            id="notes-input"
            data-testid="notes-input"
            name="notes"
            value={notes}
            maxLength={MAX_NOTES_LENGTH + 50}
            rows={3}
            placeholder="How did it move?"
            onChange={(event) => onNotesChange(event.target.value)}
            aria-invalid={(showErrors && notesError !== undefined) || undefined}
            className="bg-lab-700 placeholder:text-ash-500 min-h-20 w-full resize-y rounded-2xl px-3.5 py-3 text-[14px] leading-relaxed shadow-[inset_0_0_0_1px_var(--color-lab-600)] focus:shadow-[inset_0_0_0_1.5px_var(--color-accent)] focus:outline-none"
          />
          <span className="num text-ash-500 self-end text-[10px]">
            {notes.length}/{MAX_NOTES_LENGTH}
          </span>
          {showErrors && notesError ? (
            <span role="alert" className="text-accent text-[12px]">
              {notesError}
            </span>
          ) : null}
        </div>

        <div className="hidden flex-col gap-2 lg:flex">
          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            data-testid="finish-workout"
            disabled={isPending}
          >
            {isPending ? "Saving…" : "Finish workout"}
          </Button>
          {formError ? (
            <p role="alert" className="text-accent text-[12px] leading-relaxed">
              Couldn’t save — your session is still here. Review the error up
              top and retry.
            </p>
          ) : null}
        </div>

        <details
          data-testid="prototype-controls"
          className="ring-lab-600 rounded-2xl px-3 py-2 ring-1 ring-inset"
        >
          <summary className="text-ash-300 cursor-pointer text-[12px] font-medium">
            Prototype controls
          </summary>
          <div className="flex flex-col gap-3 py-3">
            <label
              htmlFor="simulate-failure"
              className="flex cursor-pointer items-center gap-2.5 text-[13px]"
            >
              <input
                id="simulate-failure"
                data-testid="simulate-failure"
                name="simulate_failure"
                type="checkbox"
                checked={simulateFailure}
                onChange={(event) => onSimulateChange(event.target.checked)}
                className="accent-accent size-4"
              />
              Simulate a failed save (prototype)
            </label>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              data-testid="discard-session"
              onClick={onDiscard}
              className="self-start px-0"
            >
              Discard session
            </Button>
          </div>
        </details>
      </div>
    </aside>
  );
}
