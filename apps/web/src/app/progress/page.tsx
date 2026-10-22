import type { Metadata } from "next";

import { EmptyState, ProgressIcon } from "@spottr/ui";

import { AppShell } from "~/components/app-shell";
import { PageHeader } from "~/components/page-header";

export const metadata: Metadata = { title: "Progress" };

export default function ProgressPage() {
  return (
    <AppShell>
      <PageHeader eyebrow="Trends" title="Progress" />
      <EmptyState
        eyebrow="Next up"
        title="Charts need an analytics endpoint"
        icon={<ProgressIcon className="size-9" />}
        body="The desktop mockup tracks e1RM, best sets and weekly volume per lift. Those aggregates do not exist on the API yet, so this route is reserved until the metrics handler is exposed."
      />
    </AppShell>
  );
}
