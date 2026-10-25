import { cn } from "./cn";

export interface BrandMarkProps {
  className?: string;
  title?: string;
}

/** Concentric plate mark used by the coach surfaces. */
export function BrandMark({ className, title }: BrandMarkProps) {
  return (
    <svg
      viewBox="0 0 60 60"
      className={cn("size-11", className)}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <circle cx="30" cy="30" r="27" fill="#1A1616" />
      <circle
        cx="30"
        cy="30"
        r="21"
        fill="none"
        stroke="#F0524A"
        strokeWidth="3"
      />
      <circle
        cx="30"
        cy="30"
        r="6"
        fill="#110E0E"
        stroke="#4C4141"
        strokeWidth="2"
      />
    </svg>
  );
}
