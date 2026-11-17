import Link from "next/link";

import { PageHeader } from "~/components/page-header";
import { buttonClasses, EmptyState } from "~/components/ui";

/** Friendly panel for load failures on the saved-workout route. */
export function WorkoutLoadError() {
  return (
    <>
      <PageHeader eyebrow="Session summary" title="Workout saved" />
      <EmptyState
        eyebrow="Unavailable"
        title="Couldn't load this workout"
        body="Try again in a moment, or start another session."
      >
        <Link
          href="/workouts/start"
          className={buttonClasses({ variant: "primary", size: "md" })}
        >
          Start another workout
        </Link>
      </EmptyState>
    </>
  );
}
