import type { Metadata } from "next";

import { AppShell } from "~/components/app-shell";
import { DemoNotice } from "~/components/demo-notice";
import {
  CoachNudge,
  NextWorkoutCard,
  RoutineList,
  WeekStrip,
} from "~/components/home-sections";
import { PageHeader } from "~/components/page-header";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Home" };

function todayLabel(): string {
  const now = new Date();
  const weekday = now.toLocaleDateString("en-GB", { weekday: "long" });
  const rest = now.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
  return `${weekday}, ${rest}`;
}

export default function HomePage() {
  // Monday-first index, 0–6.
  const todayIndex = (new Date().getDay() + 6) % 7;

  return (
    <AppShell>
      <PageHeader
        eyebrow={todayLabel()}
        title="Home"
        showLogo
        action={
          <span
            role="img"
            aria-label="Demo profile"
            title="Demo profile — authentication is not wired yet"
            className="flex size-10 items-center justify-center rounded-full bg-lab-800 text-sm font-semibold"
          >
            M
          </span>
        }
      />

      <DemoNotice className="mb-5">
        The next workout, routines, weekly stats and PR markers are preview
        data until those endpoints exist.
      </DemoNotice>

      <div className="flex flex-col gap-5 lg:grid lg:grid-cols-[minmax(0,1fr)_320px] lg:grid-rows-[auto_auto_1fr] lg:gap-x-6 lg:gap-y-5">
        <section className="lg:col-start-1 lg:row-start-1">
          <NextWorkoutCard />
        </section>

        <section className="lg:col-start-1 lg:row-start-2">
          <WeekStrip todayIndex={todayIndex} />
        </section>

        <aside className="order-3 lg:col-start-2 lg:row-span-3 lg:row-start-1">
          <div className="flex flex-col gap-5 lg:sticky lg:top-8">
            <CoachNudge />
          </div>
        </aside>

        <section className="order-4 lg:col-start-1 lg:row-start-3">
          <RoutineList />
        </section>
      </div>
    </AppShell>
  );
}
