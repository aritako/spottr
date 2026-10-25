import Link from "next/link";

import { BarbellIcon, EmptyState, buttonClasses } from "~/components/ui";

import { PageHeader } from "~/components/page-header";

export function StartSessionScreen() {
  return (
    <>
      <PageHeader eyebrow="Live session" title="Start workout" />
      <EmptyState
        eyebrow="Next up"
        title="Set-by-set logging"
        icon={<BarbellIcon className="size-9" />}
        body="The active-session screen (plate loader, rest timer, PR stamps) is scaffolded in the mockups but needs a workout session API. POST /workouts already accepts a full session payload."
      >
        <Link
          href="/"
          className={buttonClasses({ variant: "outline", size: "md" })}
        >
          Back to home
        </Link>
      </EmptyState>
    </>
  );
}
