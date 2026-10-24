import Link from "next/link";

import {
  BrandMark,
  Card,
  ChevronRightIcon,
  Citation,
  buttonClasses,
  cn,
} from "@spottr/ui";

import { homeFixtures, type HomeFixtures } from "~/lib/fixtures";

const dayLetters = ["M", "T", "W", "T", "F", "S", "S"] as const;
const dayNames = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;

type DayState = "done" | "pr" | "today" | "planned" | "rest";

function getDayState(
  index: number,
  week: HomeFixtures["week"],
  todayIndex: number,
): DayState {
  if (week.completedDays.includes(index)) {
    return week.prDay === index ? "pr" : "done";
  }
  if (index === todayIndex) return "today";
  if (week.plannedDays.includes(index)) return "planned";
  return "rest";
}

const dayLabels: Record<DayState, string> = {
  done: "completed",
  pr: "completed with a personal best",
  today: "today",
  planned: "planned",
  rest: "rest",
};

export function NextWorkoutCard() {
  const workout = homeFixtures.nextWorkout;

  return (
    <Card className="rounded-panel flex flex-col gap-4 p-[18px]">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <span className="eyebrow">Up next</span>
          <h2 className="display text-[26px] leading-none">{workout.name}</h2>
          <span className="text-ash-300 text-[13px]">
            {workout.exerciseCount} exercises · about {workout.minutes} min
          </span>
        </div>
        <span className="num text-ash-300 pt-0.5 text-[10px]">
          last: {workout.lastDone}
        </span>
      </div>

      <Link
        href={`/routines/${workout.slug}`}
        className={buttonClasses({ size: "lg", fullWidth: true })}
      >
        Start workout
      </Link>
    </Card>
  );
}

export function WeekStrip({ todayIndex }: { todayIndex: number }) {
  const week = homeFixtures.week;

  return (
    <section className="flex flex-col gap-3 px-1.5 lg:max-w-[440px]">
      <div className="flex items-baseline justify-between">
        <span className="eyebrow">This week</span>
        <span className="num text-ash-300 text-[11px]">
          {week.completedSessions} of {week.totalSessions} sessions
        </span>
      </div>

      <div className="grid grid-cols-7 gap-1">
        {dayLetters.map((letter, index) => {
          const state = getDayState(index, week, todayIndex);
          const isToday = index === todayIndex;

          return (
            <div
              key={`${letter}-${index}`}
              role="img"
              className="flex flex-col items-center gap-2"
              aria-label={`${dayNames[index]}: ${dayLabels[state]}`}
            >
              <span
                className={cn(
                  "eyebrow text-[8.5px]",
                  isToday && "text-bone-100",
                )}
              >
                {letter}
              </span>
              <span
                className={cn(
                  "size-7 rounded-full",
                  (state === "done" || state === "pr") && "bg-bone-100",
                  state === "pr" &&
                    "shadow-[0_0_0_2px_var(--color-lab-900),0_0_0_4px_var(--color-accent)]",
                  state === "today" &&
                    "shadow-[inset_0_0_0_1.5px_var(--color-accent)]",
                  state === "planned" &&
                    "shadow-[inset_0_0_0_1.5px_var(--color-lab-500)]",
                  state === "rest" && "bg-lab-800",
                )}
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function CoachNudge() {
  return (
    <Link
      href="/coach"
      className="rounded-card bg-lab-800 hover:bg-lab-850 flex items-start gap-3 p-4 transition-colors"
    >
      <BrandMark className="mt-0.5 size-[26px] shrink-0" />
      <div className="flex flex-1 flex-col gap-1">
        <span className="eyebrow">Coach</span>
        <p className="text-bone-300 text-sm leading-relaxed">
          {homeFixtures.coachNudge.text}{" "}
          <Citation
            index={1}
            title={homeFixtures.coachNudge.citation}
            className="align-[2px]"
          />
        </p>
      </div>
      <ChevronRightIcon className="text-ash-500 mt-1 size-4 shrink-0" />
    </Link>
  );
}

export function RoutineList() {
  return (
    <section className="flex flex-col">
      <div className="flex items-baseline justify-between px-1.5 pb-1.5">
        <span className="eyebrow">Routines</span>
        <span
          className="text-ash-500 text-xs"
          title="Routine editing lands with the routines API"
        >
          + New
        </span>
      </div>

      <div className="border-lab-800 border-t">
        {homeFixtures.routines.map((routine) => (
          <Link
            key={routine.slug}
            href={`/routines/${routine.slug}`}
            className="border-lab-800 hover:text-accent-soft flex h-14 items-center justify-between border-b text-[15px] transition-colors"
          >
            <span>{routine.name}</span>
            <span className="num text-ash-300 text-[10px]">{routine.meta}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
