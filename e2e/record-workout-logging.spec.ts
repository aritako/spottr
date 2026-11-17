import { expect, test, type Locator, type Page } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const RECORDING_PATH = path.join(
  process.cwd(),
  "docs/prototypes/workout-logging/recording.webm",
);
const API_URL = process.env.SPOTTR_API_URL ?? "http://localhost:8000";

function card(page: Page, name: string): Locator {
  return page.locator(
    `[data-testid="exercise-card"][data-exercise-name="${name}"]`,
  );
}

function setRow(page: Page, exercise: string, index: number): Locator {
  return card(page, exercise).locator('[data-testid="set-row"]').nth(index);
}

async function typeInto(locator: Locator, value: string): Promise<void> {
  await locator.click();
  await locator.press("ControlOrMeta+A");
  await locator.pressSequentially(value, { delay: 55 });
}

async function beat(page: Page, ms = 450): Promise<void> {
  await page.waitForTimeout(ms);
}

let captionStep = 0;

async function caption(page: Page, text: string): Promise<void> {
  captionStep += 1;
  await page.evaluate(
    ([step, label]) => {
      let node = document.getElementById("recording-caption");
      if (!node) {
        node = document.createElement("div");
        node.id = "recording-caption";
        node.setAttribute(
          "style",
          [
            "position:fixed",
            "left:244px",
            "bottom:20px",
            "z-index:2147483647",
            "display:flex",
            "align-items:center",
            "gap:10px",
            "padding:10px 14px",
            "border-radius:9999px",
            "background:rgba(26,22,22,0.94)",
            "box-shadow:0 0 0 1px #3A3030, 0 12px 32px rgba(0,0,0,0.45)",
            "color:#F0EBE8",
            "font:600 11px/1.2 Archivo, system-ui, sans-serif",
            "letter-spacing:0.08em",
            "text-transform:uppercase",
            "pointer-events:none",
            "backdrop-filter:blur(6px)",
          ].join(";"),
        );
        document.body.appendChild(node);
      }
      node.innerHTML = "";
      const dot = document.createElement("span");
      dot.setAttribute(
        "style",
        "width:7px;height:7px;border-radius:9999px;background:#F0524A;flex:none",
      );
      const count = document.createElement("span");
      count.setAttribute(
        "style",
        "font-family:'Martian Mono',monospace;color:#A39996;font-size:10px",
      );
      count.textContent = String(step).padStart(2, "0");
      const copy = document.createElement("span");
      copy.textContent = label;
      node.append(dot, count, copy);
    },
    [captionStep, text] as const,
  );
}

test("record the workout logging flow", async ({ page, request }) => {
  await mkdir(path.dirname(RECORDING_PATH), { recursive: true });

  const video = page.video();
  expect(video).not.toBeNull();

  let deletedWorkoutId: number | null = null;

  await page.goto("/");
  await page.addStyleTag({
    content:
      "nextjs-portal { display: none !important; } .tsqd-open-btn-container { display: none !important; }",
  });
  await expect(page.getByTestId("start-workout")).toBeVisible();
  await beat(page, 800);
  await caption(page, "Home · start a session");
  await beat(page, 900);

  await page.getByTestId("start-workout").click();
  await expect(page.getByTestId("start-session-screen")).toBeVisible();
  await beat(page, 900);
  await caption(page, "Empty session · build today's workout");

  // Add three exercises through the catalog picker.
  await caption(page, "Exercise catalog · search + pagination handled");
  await page.locator('[data-testid="add-exercise"]:visible').first().click();
  await expect(page.getByTestId("exercise-picker")).toBeVisible();
  const search = page.getByTestId("exercise-search");
  await search.click();
  await search.pressSequentially("back squat", { delay: 60 });
  await beat(page, 500);
  await page
    .locator('[data-testid="exercise-option"][data-exercise-name="Back Squat"]')
    .click();
  await beat(page, 500);

  await search.click();
  await search.press("ControlOrMeta+A");
  await search.pressSequentially("bench press", { delay: 55 });
  await beat(page, 400);
  await page
    .locator(
      '[data-testid="exercise-option"][data-exercise-name="Bench Press"]',
    )
    .click();
  await beat(page, 500);

  await search.click();
  await search.press("ControlOrMeta+A");
  await search.pressSequentially("romanian", { delay: 55 });
  await beat(page, 400);
  await page
    .locator(
      '[data-testid="exercise-option"][data-exercise-name="Romanian Deadlift"]',
    )
    .click();
  await beat(page, 600);
  await page.getByTestId("picker-done").click();
  await expect(page.getByTestId("exercise-picker")).toBeHidden();
  await beat(page, 700);
  await caption(page, "Three exercises · log weight, reps and RPE");

  // Back Squat: three working sets.
  await typeInto(
    setRow(page, "Back Squat", 0).getByTestId("set-weight"),
    "100",
  );
  await typeInto(setRow(page, "Back Squat", 0).getByTestId("set-reps"), "5");
  await typeInto(setRow(page, "Back Squat", 0).getByTestId("set-rpe"), "8");
  await beat(page, 350);

  await card(page, "Back Squat").getByTestId("add-set").click();
  await typeInto(
    setRow(page, "Back Squat", 1).getByTestId("set-weight"),
    "105",
  );
  await typeInto(setRow(page, "Back Squat", 1).getByTestId("set-rpe"), "8.5");
  await beat(page, 350);

  await card(page, "Back Squat").getByTestId("add-set").click();
  await typeInto(
    setRow(page, "Back Squat", 2).getByTestId("set-weight"),
    "110",
  );
  await typeInto(setRow(page, "Back Squat", 2).getByTestId("set-reps"), "3");
  await typeInto(setRow(page, "Back Squat", 2).getByTestId("set-rpe"), "9");
  await beat(page, 450);

  // Bench Press: two sets, then correct a reps mistake.
  await typeInto(
    setRow(page, "Bench Press", 0).getByTestId("set-weight"),
    "70",
  );
  await typeInto(setRow(page, "Bench Press", 0).getByTestId("set-reps"), "5");
  await typeInto(setRow(page, "Bench Press", 0).getByTestId("set-rpe"), "8");
  await card(page, "Bench Press").getByTestId("add-set").click();
  await typeInto(
    setRow(page, "Bench Press", 1).getByTestId("set-weight"),
    "72.5",
  );
  await typeInto(setRow(page, "Bench Press", 1).getByTestId("set-rpe"), "8.5");
  await beat(page, 400);

  await caption(page, "Correct a mistake before saving");
  await typeInto(setRow(page, "Bench Press", 0).getByTestId("set-reps"), "6");
  await beat(page, 500);

  // Romanian Deadlift: one back-off set.
  await typeInto(
    setRow(page, "Romanian Deadlift", 0).getByTestId("set-weight"),
    "80",
  );
  await typeInto(
    setRow(page, "Romanian Deadlift", 0).getByTestId("set-reps"),
    "8",
  );
  await typeInto(
    setRow(page, "Romanian Deadlift", 0).getByTestId("set-rpe"),
    "7.5",
  );
  await beat(page, 500);

  // Edit a saved value: 100 -> 102.5 kg.
  await caption(page, "Inline editing · summary recalculates");
  await typeInto(
    setRow(page, "Back Squat", 0).getByTestId("set-weight"),
    "102.5",
  );
  await beat(page, 500);

  const summary = page.getByTestId("session-total-sets");
  await expect(summary).toBeVisible();
  await page.getByTestId("session-tonnage").scrollIntoViewIfNeeded();
  await beat(page, 1400);
  await caption(page, "Session summary · one POST on finish");

  // Demonstrate the failed-save UX without losing the session.
  await page.getByTestId("prototype-controls").locator("summary").click();
  await beat(page, 400);
  await page.getByTestId("simulate-failure").check();
  await beat(page, 300);
  await page.locator('[data-testid="finish-workout"]:visible').first().click();
  const submitError = page
    .locator('[data-testid="submit-error"]:visible')
    .first();
  await expect(submitError).toBeVisible();
  await submitError.scrollIntoViewIfNeeded();
  await beat(page, 1400);
  await caption(page, "Failed save · form state preserved");
  await expect(
    setRow(page, "Back Squat", 1).getByTestId("set-weight"),
  ).toHaveValue("105");
  await expect(
    setRow(page, "Bench Press", 0).getByTestId("set-reps"),
  ).toHaveValue("6");
  await beat(page, 1400);

  await page.getByTestId("simulate-failure").uncheck();
  await beat(page, 300);
  await caption(page, "Retry · one POST persists the whole session");
  await page.locator('[data-testid="finish-workout"]:visible').first().click();

  await page.waitForURL(/\/workouts\/\d+/, { timeout: 30_000 });
  const firstWorkoutId = Number(page.url().match(/\/workouts\/(\d+)/)?.[1]);
  expect(firstWorkoutId).toBeGreaterThan(0);
  await expect(page.getByTestId("workout-saved")).toBeVisible();
  await beat(page, 900);
  await caption(page, "Saved · redirect to the session summary");
  await beat(page, 1200);

  await page.getByTestId("saved-workout-summary").scrollIntoViewIfNeeded();
  await beat(page, 1500);
  await caption(page, "Post-submit correction · no update endpoint yet");
  await page.getByTestId("delete-and-relog").click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await beat(page, 900);
  await page.getByTestId("confirm-delete").click();

  await page.waitForURL(/\/workouts\/start\?redo=1/, { timeout: 30_000 });
  await expect(page.getByTestId("relog-notice")).toBeVisible();
  await expect(
    setRow(page, "Back Squat", 0).getByTestId("set-weight"),
  ).toHaveValue("102.5");
  deletedWorkoutId = firstWorkoutId;
  await beat(page, 1200);
  await caption(page, "Delete & re-log · sets kept in the browser");

  // Fix the typo we meant to log, then finish again.
  await typeInto(
    setRow(page, "Back Squat", 0).getByTestId("set-weight"),
    "100",
  );
  await beat(page, 600);
  await caption(page, "Corrected session · save again");
  await page.locator('[data-testid="finish-workout"]:visible').first().click();
  await page.waitForURL(/\/workouts\/\d+/, { timeout: 30_000 });
  const correctedWorkoutId = Number(page.url().match(/\/workouts\/(\d+)/)?.[1]);
  await expect(page.getByTestId("workout-saved")).toBeVisible();
  await beat(page, 1400);
  await caption(page, "Correction complete · new workout persisted");
  await expect(page.getByTestId("workout-saved")).toContainText("100 × 5");
  await beat(page, 1800);

  // Verify the correction path against the API, then clean up the proof copy.
  expect(deletedWorkoutId).not.toBeNull();
  const deletedResponse = await request.get(
    `${API_URL}/workouts/${deletedWorkoutId}`,
  );
  expect(deletedResponse.status()).toBe(404);
  const correctedResponse = await request.get(
    `${API_URL}/workouts/${correctedWorkoutId}`,
  );
  expect(correctedResponse.ok()).toBeTruthy();
  const corrected = (await correctedResponse.json()) as {
    sets: { exercise_id: number; weight: number; reps: number }[];
  };
  expect(corrected.sets.length).toBe(6);

  await request.delete(`${API_URL}/workouts/${correctedWorkoutId}`);

  // The video finalises when the page closes; saveAs before that would block.
  await page.close();
  await video?.saveAs(RECORDING_PATH);
  expect(firstWorkoutId).not.toBe(correctedWorkoutId);
});
