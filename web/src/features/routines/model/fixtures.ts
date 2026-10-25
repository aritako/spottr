/**
 * Temporary fixture data for routines.
 *
 * Routines, their exercise plans and last-performance numbers are not exposed
 * by the API yet. Replace this module when the routines endpoints land; keep
 * the shapes close to the eventual response models.
 */

export interface RoutineSummary {
  slug: string;
  name: string;
  meta: string;
}

export interface RoutineExercise {
  name: string;
  target: string;
  last: string;
  note?: string;
  citation?: string;
}

export interface Routine extends RoutineSummary {
  summary: string;
  exercises: RoutineExercise[];
}

export const routines: Routine[] = [
  {
    slug: "push-a",
    name: "Push A",
    meta: "Wed · 2 PRs",
    summary: "6 exercises · 17 sets · about 60 min · last done Wed 21 Oct",
    exercises: [
      {
        name: "Bench Press",
        target: "3 × 6",
        last: "85 × 5",
        note: "New best last session. Repeat 85 for sixes.",
      },
      {
        name: "Overhead Press",
        target: "3 × 8",
        last: "50 × 8",
      },
      { name: "Incline Dumbbell Press", target: "3 × 10", last: "28 × 10" },
      { name: "Lateral Raise", target: "3 × 15", last: "10 × 15" },
      { name: "Cable Fly", target: "3 × 12", last: "15 × 12" },
      { name: "Triceps Pushdown", target: "2 × 12", last: "30 × 12" },
    ],
  },
  {
    slug: "pull-a",
    name: "Pull A",
    meta: "Fri 16 Oct",
    summary: "5 exercises · 15 sets · about 55 min · last done Fri 16 Oct",
    exercises: [
      {
        name: "Deadlift",
        target: "3 × 5",
        last: "140 × 5",
        note: "Flat 2 sessions. Try 140 × 6.",
        citation: "Last two deadlift sessions",
      },
      { name: "Weighted Pull-up", target: "3 × 8", last: "+10 × 8" },
      { name: "Barbell Row", target: "3 × 8", last: "70 × 8" },
      { name: "Face Pull", target: "3 × 15", last: "20 × 15" },
      { name: "Hammer Curl", target: "3 × 12", last: "14 × 12" },
    ],
  },
  {
    slug: "legs-a",
    name: "Legs A",
    meta: "Mon",
    summary: "5 exercises · 16 sets · about 65 min · last done Mon 19 Oct",
    exercises: [
      { name: "Back Squat", target: "3 × 5", last: "115 × 5" },
      { name: "Romanian Deadlift", target: "3 × 8", last: "100 × 8" },
      { name: "Leg Press", target: "3 × 12", last: "180 × 12" },
      { name: "Leg Curl", target: "3 × 12", last: "45 × 12" },
      { name: "Standing Calf Raise", target: "4 × 12", last: "60 × 12" },
    ],
  },
];

export function getRoutine(slug: string): Routine | undefined {
  return routines.find((routine) => routine.slug === slug);
}
