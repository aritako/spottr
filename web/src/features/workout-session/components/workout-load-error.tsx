import Link from "next/link";

import { PageHeader } from "~/components/page-header";
import { buttonClasses, EmptyState } from "~/components/ui";

/** Friendly panel for load failures on the saved-workout route. */
export function WorkoutLoadError() {
  return (
    <>
      <PageHeader eyebrow="Session complete" title="Workout saved" />
      <EmptyState
        eyebrow="Unavailable"
        title="Couldn't load this workout"
        body="The saved workout could not be loaded. Check that the API is running and try again — your data is safe."
      >
        <Link
          href="/workouts/start"
          className={buttonClasses({ variant: "primary", size: "md" })}
        >
          Log another workout
        </Link>
      </EmptyState>
    </>
  );
}
