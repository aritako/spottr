import Link from "next/link";

import { routines } from "../model/fixtures";

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
        {routines.map((routine) => (
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
