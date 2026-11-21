import { EmptyState, ProgressIcon } from "~/components/ui";

import { PageHeader } from "~/components/page-header";

export function ProgressScreen() {
  return (
    <>
      <PageHeader eyebrow="Trends" title="Progress" />
      <EmptyState
        eyebrow="Next up"
        title="Charts"
        icon={<ProgressIcon className="size-9" />}
        body="Lorem Ipsum"
      />
    </>
  );
}
