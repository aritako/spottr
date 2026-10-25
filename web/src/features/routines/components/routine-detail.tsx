import Link from "next/link";
import { notFound } from "next/navigation";

import { ChevronLeftIcon, Citation, buttonClasses } from "~/components/ui";

import { DemoNotice } from "~/components/demo-notice";
import { PageHeader } from "~/components/page-header";

import { getRoutine } from "../model/fixtures";

export function RoutineDetail({ slug }: { slug: string }) {
  const routine = getRoutine(slug);

  if (!routine) notFound();

  return (
    <div className="mx-auto w-full max-w-2xl">
      <PageHeader
        eyebrow="Routine"
        title={routine.name}
        action={
          <span
            title="Routine editing lands with the routines API"
            className="bg-lab-800 text-ash-300 flex h-10 items-center rounded-full px-4 text-[13px]"
          >
            Edit
          </span>
        }
      />

      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <Link
            href="/"
            className="text-ash-300 hover:text-bone-100 mb-1 inline-flex items-center gap-1 text-[13px]"
          >
            <ChevronLeftIcon className="size-4" />
            Home
          </Link>
          <span className="text-ash-300 text-[13px]">{routine.summary}</span>
        </div>

        <DemoNotice>
          This routine is preview data, not a routine from your log.
        </DemoNotice>

        <ol className="flex flex-col">
          {routine.exercises.map((exercise, index) => (
            <li
              key={exercise.name}
              className="border-lab-800 grid grid-cols-[26px_minmax(0,1fr)_auto] items-center gap-2.5 border-t py-3.5 last:border-b"
            >
              <span className="num text-ash-300 text-[11px]">
                {String(index + 1).padStart(2, "0")}
              </span>

              <div className="flex flex-col gap-1">
                <span className="text-[15px] font-semibold">
                  {exercise.name}
                </span>
                {exercise.note ? (
                  <span className="text-bone-300 flex items-center gap-1.5 text-xs">
                    <span className="bg-accent size-[5px] shrink-0 rounded-full" />
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
                <span className="num text-ash-300 text-[10px]">
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
  );
}
