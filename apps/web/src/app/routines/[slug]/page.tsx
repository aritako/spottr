import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import {
  ChevronLeftIcon,
  Citation,
  buttonClasses,
} from "@spottr/ui";

import { AppShell } from "~/components/app-shell";
import { PageHeader } from "~/components/page-header";
import { getRoutine } from "~/lib/fixtures";

interface RoutinePageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({
  params,
}: RoutinePageProps): Promise<Metadata> {
  const { slug } = await params;
  const routine = getRoutine(slug);
  return { title: routine ? routine.name : "Routine" };
}

export default async function RoutinePage({ params }: RoutinePageProps) {
  const { slug } = await params;
  const routine = getRoutine(slug);

  if (!routine) notFound();

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-2xl">
        <PageHeader
          eyebrow="Routine"
          title={routine.name}
          action={
            <span
              title="Routine editing lands with the routines API"
              className="flex h-10 items-center rounded-full bg-lab-800 px-4 text-[13px] text-ash-300"
            >
              Edit
            </span>
          }
        />

        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <Link
              href="/"
              className="mb-1 inline-flex items-center gap-1 text-[13px] text-ash-300 hover:text-bone-100"
            >
              <ChevronLeftIcon className="size-4" />
              Home
            </Link>
            <span className="text-[13px] text-ash-300">
              {routine.summary}
            </span>
          </div>

          <ol className="flex flex-col">
            {routine.exercises.map((exercise, index) => (
              <li
                key={exercise.name}
                className="grid grid-cols-[26px_minmax(0,1fr)_auto] items-center gap-2.5 border-t border-lab-800 py-3.5 last:border-b"
              >
                <span className="num text-[11px] text-ash-300">
                  {String(index + 1).padStart(2, "0")}
                </span>

                <div className="flex flex-col gap-1">
                  <span className="text-[15px] font-semibold">
                    {exercise.name}
                  </span>
                  {exercise.note ? (
                    <span className="flex items-center gap-1.5 text-xs text-bone-300">
                      <span className="size-[5px] shrink-0 rounded-full bg-accent" />
                      {exercise.note}
                      {exercise.citation ? (
                        <Citation
                          index={1}
                          title={exercise.citation}
                          className="align-[1px]"
                        />
                      ) : null}
                    </span>
                  ) : null}
                </div>

                <div className="flex flex-col items-end gap-1">
                  <span className="num text-[12px]">{exercise.target}</span>
                  <span className="num text-[10px] text-ash-300">
                    {exercise.last}
                  </span>
                </div>
              </li>
            ))}
          </ol>

          <div className="flex flex-col gap-2.5">
            <Link
              href="/workouts/start"
              className={buttonClasses({ size: "lg", fullWidth: true })}
            >
              Start {routine.name}
            </Link>
            <Link
              href="/"
              className={buttonClasses({
                variant: "ghost",
                className: "text-[13px]",
                fullWidth: true,
              })}
            >
              Back to home
            </Link>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
