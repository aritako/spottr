import { cn } from "./cn";

export interface LogoProps {
  className?: string;
  season?: string;
}

export function Logo({ className, season = "25" }: LogoProps) {
  return (
    <span
      className={cn(
        "display inline-flex items-baseline leading-none tracking-[0.04em]",
        className,
      )}
    >
      Spottr
      <span className="text-accent">/</span>
      <span className="text-ash-300">{season}</span>
    </span>
  );
}
