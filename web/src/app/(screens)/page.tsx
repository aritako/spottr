import type { Metadata } from "next";

import { HomeScreen } from "~/features/home";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Home" };

export default function HomePage() {
  return <HomeScreen />;
}
