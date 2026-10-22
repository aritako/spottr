import type { ReactNode } from "react";

import { cn } from "./cn";

export interface CitationProps {
  index: number | string;
  href?: string;
  className?: string;
  title?: string;
  children?: ReactNode;
}

export function Citation({
  index,
  href,
  className,
  title,
  children,
}: CitationProps) {
  const classes = cn(
    "num inline-flex h-4 min-w-4 items-center justify-center rounded-[5px] bg-accent/15 px-1 text-[9px] text-accent",
    className,
  );

  if (href) {
    return (
      <a className={classes} href={href} title={title}>
        {children ?? index}
      </a>
    );
  }

  return (
    <sup className={classes} title={title}>
      {children ?? index}
    </sup>
  );
}
