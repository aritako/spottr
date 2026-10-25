import type { Metadata } from "next";

import { CoachScreen } from "~/features/coach";

export const metadata: Metadata = { title: "Coach" };

export default function CoachPage() {
  return <CoachScreen />;
}
