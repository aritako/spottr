import Link from "next/link";

import { PageHeader } from "~/components/page-header";
import { buttonClasses, EmptyState } from "~/components/ui";

import { loadExerciseCatalog } from "../api/exercises";
import { SessionBuilder } from "./session-builder";

/** Start screen root: loads the catalog server-side, then hands to the builder. */
export async function StartSessionScreen() {
  let catalog: Awaited<ReturnType<typeof loadExerciseCatalog>> | null = null;
  try {
    catalog = await loadExerciseCatalog();
  } catch {
    catalog = null;
  }

  return (
    <div data-testid="start-session-screen">
      {catalog === null ? (
        <>
          <PageHeader eyebrow="Live session" title="Start workout" />
          <EmptyState
            eyebrow="Catalog unavailable"
            title="Couldn't load exercises"
            body="Exercises didn't load. Try again — nothing is lost."
          >
            <Link
              href="/workouts/start"
              className={buttonClasses({ variant: "primary", size: "md" })}
            >
              Try again
            </Link>
          </EmptyState>
        </>
      ) : (
        <SessionBuilder catalog={catalog} />
      )}
    </div>
  );
}
