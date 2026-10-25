import { DemoNotice } from "~/components/demo-notice";
import { PageHeader } from "~/components/page-header";
import { RoutineList } from "~/features/routines";

import { CoachNudge, NextWorkoutCard, WeekStrip } from "./home-sections";

function todayLabel(): string {
  const now = new Date();
  const weekday = now.toLocaleDateString("en-GB", { weekday: "long" });
  const rest = now.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
  });
  return `${weekday}, ${rest}`;
}

export function HomeScreen() {
  // Monday-first index, 0–6.
  const todayIndex = (new Date().getDay() + 6) % 7;

  return (
    <>
      <PageHeader
        eyebrow={todayLabel()}
        title="Home"
        showLogo
        action={
          <span
            role="img"
            aria-label="Demo profile"
            title="Demo profile — authentication is not wired yet"
            className="bg-lab-800 flex size-10 items-center justify-center rounded-full text-sm font-semibold"
          >
            M
          </span>
        }
      />

      <DemoNotice className="mb-5">
        The next workout, routines, weekly stats and PR markers are preview data
        until those endpoints exist.
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
    </>
  );
}
