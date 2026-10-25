import { EmptyState, HistoryIcon } from "~/components/ui";

import { PageHeader } from "~/components/page-header";

export function HistoryScreen() {
  return (
    <>
      <PageHeader eyebrow="Training log" title="History" />
      <EmptyState
        eyebrow="Next up"
        title="The log goes here"
        icon={<HistoryIcon className="size-9" />}
        body="Session history is the next screen to wire. GET /workouts already returns paginated sessions with their sets, so this page can render real rows as soon as the web client lands."
      />
    </>
  );
}
