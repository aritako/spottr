import type { Metadata } from "next";

import { AppShell } from "~/components/app-shell";

import { CoachScreen } from "./coach-screen";

export const metadata: Metadata = { title: "Coach" };

export default function CoachPage() {
  return (
    <AppShell>
      <CoachScreen />
    </AppShell>
  );
}
