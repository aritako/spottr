import type { ReactNode } from "react";

import { cn } from "@spottr/ui";

export function DemoNotice({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "bg-lab-800/70 text-ash-300 ring-lab-600 flex items-start gap-2 rounded-2xl px-3 py-2 text-[11px] leading-relaxed ring-1 ring-inset",
        className,
      )}
    >
      <span className="bg-accent/15 text-accent mt-px shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.12em]">
        Demo
      </span>
      <span>{children}</span>
    </p>
  );
}
