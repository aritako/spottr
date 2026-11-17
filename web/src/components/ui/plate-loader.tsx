import { cn } from "./cn";

/** Standard bar weight in kilograms. */
export const BAR_WEIGHT_KG = 20;

/** Plate denominations available per side, heaviest first. */
const PLATE_STEPS = [25, 20, 15, 10, 5, 2.5, 1.25] as const;

/** Greedy plates-per-side split for a loaded barbell. */
export function platesForWeight(weightKg: number): number[] {
  if (!Number.isFinite(weightKg) || weightKg <= BAR_WEIGHT_KG) return [];
  let remaining = (weightKg - BAR_WEIGHT_KG) / 2;
  const plates: number[] = [];
  for (const step of PLATE_STEPS) {
    while (remaining >= step - 1e-9 && plates.length < 8) {
      plates.push(step);
      remaining -= step;
    }
  }
  return plates;
}

function plateHeight(plate: number): number {
  switch (plate) {
    case 25:
      return 60;
    case 20:
      return 48;
    case 15:
      return 42;
    case 10:
      return 34;
    case 5:
      return 28;
    case 2.5:
      return 22;
    default:
      return 16;
  }
}

function plateWidth(plate: number): number {
  switch (plate) {
    case 25:
      return 14;
    case 20:
      return 11;
    case 15:
      return 10;
    case 10:
      return 8;
    case 5:
      return 8;
    case 2.5:
      return 6;
    default:
      return 6;
  }
}

function plateFill(plate: number): string {
  switch (plate) {
    case 25:
      return "fill-accent";
    case 20:
      return "fill-ash-500";
    case 15:
      return "fill-ash-400";
    case 10:
      return "fill-ash-300";
    case 5:
      return "fill-bone-300";
    case 2.5:
      return "fill-ash-400";
    default:
      return "fill-ash-500";
  }
}

export interface PlateLoaderProps {
  /** Total loaded weight in kilograms, including the 20 kg bar. */
  weightKg: number;
  /** Accessible label. Omit for purely decorative use (aria-hidden). */
  label?: string;
  className?: string;
}

/**
 * Compact barbell visual: 20 kg bar with per-side plates for the given load.
 * Generic and decorative; parents own any caption text.
 */
export function PlateLoader({ weightKg, label, className }: PlateLoaderProps) {
  const plates = platesForWeight(weightKg);

  let cursor = 150;
  const left = plates.map((plate) => {
    const width = plateWidth(plate);
    const x = cursor - width;
    cursor = x - 2;
    return { plate, x, width };
  });
  const collarX = cursor - 10;
  const right = left.map(({ plate, x, width }) => ({
    plate,
    x: 340 - x - width,
    width,
  }));
  const rightCollarX = 340 - collarX - 8;

  return (
    <svg
      viewBox="0 0 340 72"
      className={cn("h-14 w-full", className)}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <line
        x1="8"
        y1="36"
        x2="332"
        y2="36"
        className="stroke-ash-400"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <line
        x1="150"
        y1="36"
        x2="190"
        y2="36"
        className="stroke-lab-400"
        strokeWidth="3"
        strokeDasharray="2 2"
      />
      {left.map(({ plate, x, width }, index) => (
        <rect
          key={`l-${plate}-${index}`}
          x={x}
          y={36 - plateHeight(plate) / 2}
          width={width}
          height={plateHeight(plate)}
          rx="2"
          className={plateFill(plate)}
        />
      ))}
      {right.map(({ plate, x, width }, index) => (
        <rect
          key={`r-${plate}-${index}`}
          x={x}
          y={36 - plateHeight(plate) / 2}
          width={width}
          height={plateHeight(plate)}
          rx="2"
          className={plateFill(plate)}
        />
      ))}
      <rect
        x={collarX}
        y="27"
        width="8"
        height="18"
        rx="2"
        className="fill-ash-400"
      />
      <rect
        x={rightCollarX}
        y="27"
        width="8"
        height="18"
        rx="2"
        className="fill-ash-400"
      />
    </svg>
  );
}
