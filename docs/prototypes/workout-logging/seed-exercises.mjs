#!/usr/bin/env node
/**
 * Add the accessory exercises the workout-logging prototype uses for
 * pagination. The core five lifts are created by scripts/seed.py; this script
 * is idempotent and only POSTs names that are missing.
 *
 * Usage:
 *   SPOTTR_API_URL=http://localhost:8000 node docs/prototypes/workout-logging/seed-exercises.mjs
 */

const baseUrl = (process.env.SPOTTR_API_URL ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);

const exercises = [
  ["Front Squat", "squat", true],
  ["Incline Bench Press", "horizontal_push", true],
  ["Romanian Deadlift", "hinge", true],
  ["Dumbbell Row", "horizontal_pull", true],
  ["Chin-up", "vertical_pull", true],
  ["Pull-up", "vertical_pull", true],
  ["Dip", "vertical_push", true],
  ["Lateral Raise", "isolation", false],
  ["Leg Press", "squat", true],
  ["Bulgarian Split Squat", "lunge", true],
  ["Plank", "core", false],
  ["Cable Fly", "horizontal_push", false],
  ["Face Pull", "horizontal_pull", false],
  ["Hammer Curl", "isolation", false],
  ["Leg Curl", "isolation", false],
  ["Leg Extension", "isolation", false],
];

async function getAllExercises() {
  const all = [];
  for (let page = 0; page < 50; page += 1) {
    const response = await fetch(
      `${baseUrl}/exercises?page=${page}&page_size=100`,
    );
    if (!response.ok) {
      throw new Error(`GET /exercises failed with ${response.status}`);
    }
    const batch = await response.json();
    all.push(...batch);
    if (batch.length < 100) break;
  }
  return all;
}

async function main() {
  const existing = await getAllExercises();
  const names = new Set(existing.map((exercise) => exercise.name));
  let added = 0;

  for (const [name, category, isCompound] of exercises) {
    if (names.has(name)) continue;
    const response = await fetch(`${baseUrl}/exercises`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        category,
        is_compound: isCompound,
      }),
    });
    if (!response.ok) {
      throw new Error(
        `POST /exercises (${name}) failed with ${response.status}`,
      );
    }
    added += 1;
  }

  console.log(
    `Catalog: ${existing.length + added} exercises (${added} added, ${
      existing.length
    } already present).`,
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
