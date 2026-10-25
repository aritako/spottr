import { EmptyState, ProgressIcon } from "~/components/ui";

import { PageHeader } from "~/components/page-header";

export function ProgressScreen() {
  return (
    <>
      <PageHeader eyebrow="Trends" title="Progress" />
      <EmptyState
        eyebrow="Next up"
        title="Charts need an analytics endpoint"
        icon={<ProgressIcon className="size-9" />}
        body="The desktop mockup tracks e1RM, best sets and weekly volume per lift. Those aggregates do not exist on the API yet, so this route is reserved until the metrics handler is exposed."
      />
    </>
  );
}
