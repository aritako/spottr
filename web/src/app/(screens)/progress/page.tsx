import type { Metadata } from "next";

import { ProgressScreen } from "~/features/progress";

export const metadata: Metadata = { title: "Progress" };

export default function ProgressPage() {
  return <ProgressScreen />;
}
