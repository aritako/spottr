import type { Metadata } from "next";

import { EmptyState, HistoryIcon } from "@spottr/ui";

import { AppShell } from "~/components/app-shell";
import { PageHeader } from "~/components/page-header";

export const metadata: Metadata = { title: "History" };

export default function HistoryPage() {
  return (
    <AppShell>
      <PageHeader eyebrow="Training log" title="History" />
      <EmptyState
        eyebrow="Next up"
        title="The log goes here"
        icon={<HistoryIcon className="size-9" />}
        body="Session history is the next screen to wire. GET /workouts already returns paginated sessions with their sets, so this page can render real rows as soon as the web client lands."
      />
    </AppShell>
  );
}
