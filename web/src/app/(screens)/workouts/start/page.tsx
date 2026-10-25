import type { Metadata } from "next";

import { StartSessionScreen } from "~/features/workout-session";

export const metadata: Metadata = { title: "Start workout" };

export default function StartWorkoutPage() {
  return <StartSessionScreen />;
}
