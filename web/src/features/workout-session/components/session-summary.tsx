import { Button, PlateLoader, cn, platesForWeight } from "~/components/ui";

import { MAX_NOTES_LENGTH } from "../model/constants";
import { formatKg, type SessionTotals } from "../model/session";

interface SessionSummaryProps {
  totals: SessionTotals;
  topSetLabel: string | null;
  notes: string;
  notesError?: string;
  showErrors: boolean;
  errorCount: number;
  isPending: boolean;
  onNotesChange: (value: string) => void;
  simulateFailure: boolean;
  onSimulateChange: (value: boolean) => void;
  onDiscard: () => void;
  className?: string;
}

function Figure({
  label,
  testid,
  children,
}: {
  label: string;
  testid?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-ash-400 text-[11px] uppercase tracking-[0.1em]">
        {label}
      </dt>
      <dd data-testid={testid} className="num text-[14px] leading-none">
        {children}
      </dd>
    </div>
  );
}

/** Sidebar receipt: totals, bar load, note, finish. */
export function SessionSummary({
  totals,
  topSetLabel,
  notes,
  notesError,
  showErrors,
  errorCount,
  isPending,
  onNotesChange,
  simulateFailure,
  onSimulateChange,
  onDiscard,
  className,
}: SessionSummaryProps) {
  const topWeight = totals.topSet?.weight ?? 0;
  const plates = platesForWeight(topWeight);
  const showPlates = totals.topSet !== null;
  const caption =
    plates.length > 0
      ? `20 kg bar · ${plates.join(" + ")} per side`
      : "20 kg bar";

  return (
    <aside
      aria-label="Session summary"
      className={cn("lg:sticky lg:top-8", className)}
    >
      <div className="rounded-panel bg-lab-800 flex flex-col gap-5 p-5">
        <dl className="flex flex-col gap-2.5">
          <Figure label="Sets" testid="session-total-sets">
            {totals.sets}
          </Figure>
          <Figure label="Tonnage" testid="session-tonnage">
            {formatKg(totals.tonnage)} kg
          </Figure>
          <Figure label="Top set" testid="session-top-set">
            {topSetLabel ?? "—"}
          </Figure>
        </dl>

        {showPlates ? (
          <figure className="flex flex-col gap-1">
            <PlateLoader
              className="h-12"
              weightKg={topWeight}
              label={`Barbell loaded to ${formatKg(topWeight)} kilograms: 20 kilogram bar plus ${plates.join(", ")} kilograms per side.`}
            />
            <figcaption className="num text-ash-400 text-center text-[11px]">
              {caption}
            </figcaption>
          </figure>
        ) : null}

        <div className="border-lab-700/70 flex flex-col gap-1.5 border-t pt-4">
          <label htmlFor="notes-input" className="sr-only">
            Session notes
          </label>
          <textarea
            id="notes-input"
            data-testid="notes-input"
            name="notes"
            value={notes}
            maxLength={MAX_NOTES_LENGTH}
            rows={2}
            placeholder="Add a note (optional)"
            onChange={(event) => onNotesChange(event.target.value)}
            aria-invalid={(showErrors && notesError !== undefined) || undefined}
            className="bg-lab-700/60 placeholder:text-ash-400 min-h-16 w-full resize-y rounded-xl px-3.5 py-2.5 text-[13px] leading-relaxed shadow-[inset_0_0_0_1px_var(--color-lab-600)] focus:shadow-[inset_0_0_0_1.5px_var(--color-accent)]"
          />
          {notes.length > MAX_NOTES_LENGTH - 60 ? (
            <span className="num text-ash-400 self-end text-[10px]">
              {MAX_NOTES_LENGTH - notes.length} left
            </span>
          ) : null}
          {showErrors && notesError ? (
            <span role="alert" className="text-accent text-[12px]">
              {notesError}
            </span>
          ) : null}
        </div>

        <div className="hidden flex-col gap-2 lg:flex">
          {showErrors && errorCount > 0 ? (
            <p role="status" className="text-accent text-[12px] leading-snug">
              Fix {errorCount} {errorCount === 1 ? "field" : "fields"} before
              finishing.
            </p>
          ) : null}
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
        </div>

        <details data-testid="prototype-controls" className="group pt-1">
          <summary className="text-ash-400 cursor-pointer text-[11px]">
            Prototype controls
          </summary>
          <div className="flex flex-col gap-3 pb-1 pt-3">
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
              Simulate a failed save
            </label>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              data-testid="discard-session"
              onClick={onDiscard}
              className="text-ash-300 hover:text-bone-100 self-start px-0"
            >
              Discard session
            </Button>
          </div>
        </details>
      </div>
    </aside>
  );
}
