import type { Exercise } from "@spottr/api-client";

import {
  DRAFT_STORAGE_KEY,
  MAX_NOTES_LENGTH,
  MAX_REPS,
  MAX_RPE,
  MAX_WEIGHT_KG,
  RELOG_STORAGE_KEY,
} from "./constants";

/** One editable set row. Values stay strings so half-typed input survives. */
export interface DraftSet {
  key: string;
  weight: string;
  reps: string;
  rpe: string;
}

/** One exercise card in the session builder. */
export interface DraftExercise {
  key: string;
  exerciseId: number;
  sets: DraftSet[];
}

/** Payload row sent to the server action (numbers; NaN becomes null in JSON). */
export interface DraftSetPayload {
  exerciseId: number;
  weight: number;
  reps: number;
  rpe: number | null;
  setIndex: number;
}

export interface SetFieldErrors {
  weight?: string;
  reps?: string;
  rpe?: string;
}

export interface SessionValidation {
  /** Human-readable summary, shown near the finish action and up top. */
  summary: string[];
  /** Field errors keyed by set key. */
  setErrors: Record<string, SetFieldErrors>;
  /** Card-level errors keyed by exercise block key. */
  blockErrors: Record<string, string>;
  notesError?: string;
}

export interface SessionTotals {
  exercises: number;
  sets: number;
  tonnage: number;
  topSet: { weight: number; reps: number } | null;
}

/** Accept the comma decimal that kg-region phone keyboards produce. */
function normalizeDecimal(raw: string): string {
  const value = raw.trim();
  return value.includes(",") && !value.includes(".")
    ? value.replace(",", ".")
    : value;
}

function parseWeight(raw: string): number | null {
  const value = normalizeDecimal(raw);
  if (value === "") return null;
  if (!/^\d+(\.\d{1,2})?$/.test(value)) return Number.NaN;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function parseReps(raw: string): number | null {
  const value = raw.trim();
  if (value === "") return null;
  if (!/^\d+$/.test(value)) return Number.NaN;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function parseRpe(raw: string): number | null {
  const value = normalizeDecimal(raw);
  if (value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

/** Client-side validation mirroring the server action rules. */
export function validateSession(
  blocks: DraftExercise[],
  notes: string,
  nameOf: (exerciseId: number) => string,
): SessionValidation {
  const summary: string[] = [];
  const setErrors: Record<string, SetFieldErrors> = {};
  const blockErrors: Record<string, string> = {};
  let notesError: string | undefined;

  if (blocks.length === 0) {
    summary.push("Add at least one exercise to start your session.");
  }

  for (const block of blocks) {
    const name = nameOf(block.exerciseId);
    if (block.sets.length === 0) {
      blockErrors[block.key] = `${name} needs at least one set.`;
      summary.push(`${name} needs at least one set.`);
      continue;
    }
    block.sets.forEach((set, index) => {
      const fields: SetFieldErrors = {};
      const label = `${name} set ${index + 1}`;

      const rawWeight = set.weight.trim();
      const weight = parseWeight(rawWeight);
      if (weight === null) {
        fields.weight = "Required";
        summary.push(`${label}: enter a load in kg.`);
      } else if (Number.isNaN(weight)) {
        const numeric = Number(rawWeight);
        if (
          Number.isFinite(numeric) &&
          (numeric < 0 || numeric > MAX_WEIGHT_KG)
        ) {
          fields.weight = `0–${MAX_WEIGHT_KG} kg`;
          summary.push(`${label}: load must be 0–${MAX_WEIGHT_KG} kg.`);
        } else {
          fields.weight = "2 decimals max";
          summary.push(`${label}: use a load like 82.5, up to 2 decimals.`);
        }
      } else if (weight < 0 || weight > MAX_WEIGHT_KG) {
        fields.weight = `0–${MAX_WEIGHT_KG} kg`;
        summary.push(`${label}: load must be 0–${MAX_WEIGHT_KG} kg.`);
      }

      const reps = parseReps(set.reps);
      if (reps === null) {
        fields.reps = "Required";
        summary.push(`${label}: enter reps.`);
      } else if (Number.isNaN(reps)) {
        fields.reps = `1–${MAX_REPS}`;
        summary.push(
          `${label}: reps must be a whole number from 1–${MAX_REPS}.`,
        );
      } else if (reps < 1 || reps > MAX_REPS) {
        fields.reps = `1–${MAX_REPS}`;
        summary.push(
          `${label}: reps must be a whole number from 1–${MAX_REPS}.`,
        );
      }

      const rpe = parseRpe(set.rpe);
      if (rpe !== null && Number.isNaN(rpe)) {
        fields.rpe = `0–${MAX_RPE}`;
        summary.push(`${label}: RPE must be a number from 0 to ${MAX_RPE}.`);
      } else if (rpe !== null && (rpe < 0 || rpe > MAX_RPE)) {
        fields.rpe = `0–${MAX_RPE}`;
        summary.push(`${label}: RPE must be 0–${MAX_RPE}.`);
      }

      if (fields.weight ?? fields.reps ?? fields.rpe) {
        setErrors[set.key] = fields;
      }
    });
  }

  if (notes.length > MAX_NOTES_LENGTH) {
    notesError = `Keep notes under ${MAX_NOTES_LENGTH} characters.`;
    summary.push(notesError);
  }

  return { summary, setErrors, blockErrors, notesError };
}

/** Totals over the sets that parse as valid numbers. */
export function computeTotals(blocks: DraftExercise[]): SessionTotals {
  let sets = 0;
  let tonnage = 0;
  let topSet: { weight: number; reps: number } | null = null;

  for (const block of blocks) {
    for (const set of block.sets) {
      const weight = parseWeight(set.weight);
      const reps = parseReps(set.reps);
      if (
        weight === null ||
        Number.isNaN(weight) ||
        weight < 0 ||
        weight > MAX_WEIGHT_KG ||
        reps === null ||
        !Number.isInteger(reps) ||
        reps < 1 ||
        reps > MAX_REPS
      ) {
        continue;
      }
      sets += 1;
      tonnage += weight * reps;
      if (
        topSet === null ||
        weight > topSet.weight ||
        (weight === topSet.weight && reps > topSet.reps)
      ) {
        topSet = { weight, reps };
      }
    }
  }

  return { exercises: blocks.length, sets, tonnage, topSet };
}

/** Flatten the draft into API-shaped rows with per-exercise set indexes. */
export function buildSetsPayload(blocks: DraftExercise[]): DraftSetPayload[] {
  return blocks.flatMap((block) =>
    block.sets.map((set, setIndex) => ({
      exerciseId: block.exerciseId,
      weight: parseWeight(set.weight) ?? Number.NaN,
      reps: parseReps(set.reps) ?? Number.NaN,
      rpe: parseRpe(set.rpe),
      setIndex,
    })),
  );
}

/** "horizontal_push" -> "horizontal push". */
export function formatCategory(category: string | null): string {
  if (!category) return "Uncategorized";
  return category.replace(/_/g, " ");
}

const kgFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
});

/** 0 -> "00:00", 3725 -> "1:02:05". */
export function formatClock(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  const mm = String(minutes).padStart(2, "0");
  const ss = String(rest).padStart(2, "0");
  return hours > 0 ? `${hours}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** 42 * 60 -> "42 min". Rounded to the minute. */
export function formatDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  if (seconds < 60) return "<1 min";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}

/** "1240" -> "1,240". Keeps one decimal when the value has one. */
export function formatKg(value: number): string {
  return kgFormatter.format(value);
}

export function formatPerformedAt(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const day = new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(date);
  const time = new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
  return `${day} · ${time}`;
}

/** Serializable delete-and-re-log handoff kept in sessionStorage. */
export interface RelogHandoff {
  version: 1;
  performedAt: string;
  notes: string;
  exercises: Array<{
    exerciseId: number;
    sets: Array<{ weight: string; reps: string; rpe: string }>;
  }>;
}

export function writeRelogHandoff(handoff: RelogHandoff): void {
  try {
    sessionStorage.setItem(RELOG_STORAGE_KEY, JSON.stringify(handoff));
  } catch {
    // Private mode or quota: the builder simply starts empty.
  }
}

function normalizeHandoff(parsed: unknown): RelogHandoff | null {
  if (
    !parsed ||
    typeof parsed !== "object" ||
    (parsed as { version?: unknown }).version !== 1 ||
    typeof (parsed as { performedAt?: unknown }).performedAt !== "string" ||
    !Array.isArray((parsed as { exercises?: unknown }).exercises)
  ) {
    return null;
  }
  const handoff = parsed as RelogHandoff;
  if (Number.isNaN(Date.parse(handoff.performedAt))) return null;
  return {
    version: 1,
    performedAt: handoff.performedAt,
    notes: typeof handoff.notes === "string" ? handoff.notes : "",
    exercises: handoff.exercises
      .filter(
        (entry) =>
          entry &&
          typeof entry.exerciseId === "number" &&
          Array.isArray(entry.sets),
      )
      .map((entry) => ({
        exerciseId: entry.exerciseId,
        sets: entry.sets
          .filter((set) => set && typeof set === "object")
          .map((set) => ({
            weight: typeof set.weight === "string" ? set.weight : "",
            reps: typeof set.reps === "string" ? set.reps : "",
            rpe: typeof set.rpe === "string" ? set.rpe : "",
          })),
      })),
  };
}

export function readRelogHandoff(): RelogHandoff | null {
  try {
    const raw = sessionStorage.getItem(RELOG_STORAGE_KEY);
    if (!raw) return null;
    return normalizeHandoff(JSON.parse(raw));
  } catch {
    return null;
  }
}

/** In-progress workout. localStorage so a discarded tab can still resume. */
export interface StoredDraft extends RelogHandoff {
  isRedo: boolean;
}

export function writeDraft(draft: StoredDraft): void {
  try {
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
  } catch {
    // Private mode or quota: the session simply does not persist.
  }
}

export function readDraft(): StoredDraft | null {
  let parsed: unknown;
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) return null;
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  const handoff = normalizeHandoff(parsed);
  if (!handoff) return null;
  const isRedo = Boolean(
    parsed &&
    typeof parsed === "object" &&
    (parsed as { isRedo?: unknown }).isRedo === true,
  );
  return { ...handoff, isRedo };
}

export function clearDraft(): void {
  try {
    localStorage.removeItem(DRAFT_STORAGE_KEY);
  } catch {
    // Nothing to clear.
  }
}

/** 24 hours: long enough to survive a tab discard, short enough to be stale. */
export function isFreshDraft(draft: StoredDraft): boolean {
  const started = Date.parse(draft.performedAt);
  if (Number.isNaN(started)) return false;
  return Date.now() - started < 24 * 60 * 60 * 1000;
}

export function clearRelogHandoff(): void {
  try {
    sessionStorage.removeItem(RELOG_STORAGE_KEY);
  } catch {
    // Nothing to clear.
  }
}

export function exerciseNameById(
  catalog: Exercise[],
  exerciseId: number,
): string {
  return (
    catalog.find((entry) => entry.id === exerciseId)?.name ?? "Unknown exercise"
  );
}
