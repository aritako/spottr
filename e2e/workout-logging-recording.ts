import {
  expect,
  type APIRequestContext,
  type Locator,
  type Page,
} from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

export const RECORDING_DIR = path.join(
  process.cwd(),
  "docs/prototypes/workout-logging",
);
export const DESKTOP_RECORDING_PATH = path.join(
  RECORDING_DIR,
  "recording.webm",
);
export const MOBILE_RECORDING_PATH = path.join(
  RECORDING_DIR,
  "recording-mobile.webm",
);
const API_URL = process.env.SPOTTR_API_URL ?? "http://localhost:8000";

export const DESKTOP = { width: 1440, height: 900 } as const;
export const MOBILE = { width: 390, height: 844 } as const;

export const videoOptions = (size: { width: number; height: number }) => ({
  mode: "on" as const,
  size,
});

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

async function setRpe(row: Locator, value: string): Promise<void> {
  const rpe = row.getByTestId("set-rpe");
  const tag = await rpe.evaluate((el) => el.tagName);
  if (tag === "SELECT") await rpe.selectOption(value);
  else await typeInto(rpe, value);
}

async function completeAll(page: Page): Promise<void> {
  const toggles = page.locator('[data-testid="toggle-set"]');
  const count = await toggles.count();
  for (let index = 0; index < count; index += 1) {
    await toggles.nth(index).click();
  }
}

async function beat(page: Page, ms = 450): Promise<void> {
  await page.waitForTimeout(ms);
}

let captionStep = 0;

async function caption(page: Page, text: string): Promise<void> {
  captionStep += 1;
  await page.evaluate(
    ([step, label]) => {
      const mobile = window.innerWidth < 640;
      let node = document.getElementById("recording-caption");
      if (!node) {
        node = document.createElement("div");
        node.id = "recording-caption";
        node.setAttribute(
          "style",
          [
            "position:fixed",
            mobile ? "left:12px" : "left:50%",
            mobile ? "bottom:180px" : "bottom:20px",
            mobile ? "transform:none" : "transform:translateX(-50%)",
            "z-index:2147483647",
            "display:flex",
            "align-items:center",
            "gap:8px",
            mobile ? "padding:8px 11px" : "padding:10px 14px",
            "border-radius:9999px",
            "background:rgba(26,22,22,0.94)",
            "box-shadow:0 0 0 1px #3A3030, 0 12px 32px rgba(0,0,0,0.45)",
            "color:#F0EBE8",
            mobile
              ? "font:600 10.5px/1.3 Archivo, system-ui, sans-serif"
              : "font:600 11.5px/1.3 Archivo, system-ui, sans-serif",
            "letter-spacing:0.01em",
            "text-transform:none",
            "max-width:calc(100vw - 24px)",
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
        "font-family:'Martian Mono',monospace;color:#A39996;font-size:9px",
      );
      count.textContent = String(step).padStart(2, "0");
      const copy = document.createElement("span");
      copy.textContent = label;
      node.append(dot, count, copy);
    },
    [captionStep, text] as const,
  );
}

export async function recordFlow(
  page: Page,
  request: APIRequestContext,
  outputPath: string,
): Promise<void> {
  captionStep = 0;
  await mkdir(path.dirname(outputPath), { recursive: true });

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
  await caption(page, "Home");
  await beat(page, 900);

  await page.getByTestId("start-workout").click();
  await expect(page.getByTestId("start-session-screen")).toBeVisible();
  await beat(page, 900);
  await caption(page, "Start a workout");

  // Add three exercises through the catalog picker.
  await caption(page, "Find an exercise");
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
  await caption(page, "Three exercises, six sets");

  // Back Squat: three working sets.
  await typeInto(
    setRow(page, "Back Squat", 0).getByTestId("set-weight"),
    "100",
  );
  await typeInto(setRow(page, "Back Squat", 0).getByTestId("set-reps"), "5");
  await setRpe(setRow(page, "Back Squat", 0), "8");
  await beat(page, 350);

  await card(page, "Back Squat").getByTestId("add-set").click();
  await typeInto(
    setRow(page, "Back Squat", 1).getByTestId("set-weight"),
    "105",
  );
  await typeInto(setRow(page, "Back Squat", 1).getByTestId("set-reps"), "5");
  await setRpe(setRow(page, "Back Squat", 1), "8.5");
  await beat(page, 350);

  await card(page, "Back Squat").getByTestId("add-set").click();
  await typeInto(
    setRow(page, "Back Squat", 2).getByTestId("set-weight"),
    "110",
  );
  await typeInto(setRow(page, "Back Squat", 2).getByTestId("set-reps"), "3");
  await setRpe(setRow(page, "Back Squat", 2), "9");
  await beat(page, 450);

  // Bench Press: two sets, then correct a reps mistake.
  await typeInto(
    setRow(page, "Bench Press", 0).getByTestId("set-weight"),
    "70",
  );
  await typeInto(setRow(page, "Bench Press", 0).getByTestId("set-reps"), "5");
  await setRpe(setRow(page, "Bench Press", 0), "8");
  await card(page, "Bench Press").getByTestId("add-set").click();
  await typeInto(
    setRow(page, "Bench Press", 1).getByTestId("set-weight"),
    "72.5",
  );
  await typeInto(setRow(page, "Bench Press", 1).getByTestId("set-reps"), "6");
  await setRpe(setRow(page, "Bench Press", 1), "8.5");
  await beat(page, 400);

  await caption(page, "Fix a typo");
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
  await setRpe(setRow(page, "Romanian Deadlift", 0), "7.5");
  await beat(page, 500);

  // Edit a saved value: 100 -> 102.5 kg.
  await caption(page, "Live totals");
  await typeInto(
    setRow(page, "Back Squat", 0).getByTestId("set-weight"),
    "102.5",
  );
  await beat(page, 500);

  await completeAll(page);
  const summary = page.getByTestId("session-total-sets");
  await expect(summary).toBeVisible();
  await page.getByTestId("session-tonnage").scrollIntoViewIfNeeded();
  await beat(page, 1400);

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
  await caption(page, "Save failed, sets kept");
  await expect(
    setRow(page, "Back Squat", 1).getByTestId("set-weight"),
  ).toHaveValue("105");
  await expect(
    setRow(page, "Bench Press", 0).getByTestId("set-reps"),
  ).toHaveValue("6");
  await beat(page, 1400);

  await page.getByTestId("simulate-failure").uncheck();
  await beat(page, 300);
  await caption(page, "Try again");
  await page.locator('[data-testid="finish-workout"]:visible').first().click();

  await page.waitForURL(/\/workouts\/\d+/, { timeout: 30_000 });
  const firstWorkoutId = Number(page.url().match(/\/workouts\/(\d+)/)?.[1]);
  expect(firstWorkoutId).toBeGreaterThan(0);
  await expect(page.getByTestId("workout-saved")).toBeVisible();
  await beat(page, 900);
  await caption(page, "Saved");
  await beat(page, 1200);

  await page.getByTestId("saved-workout-summary").scrollIntoViewIfNeeded();
  await beat(page, 1500);
  await caption(page, "Delete and re-log");
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
  await caption(page, "Sets kept");

  // Fix the typo we meant to log, then finish again.
  await typeInto(
    setRow(page, "Back Squat", 0).getByTestId("set-weight"),
    "100",
  );
  await beat(page, 600);
  await caption(page, "Fix and save");
  await page.locator('[data-testid="finish-workout"]:visible').first().click();
  await page.waitForURL(/\/workouts\/\d+/, { timeout: 30_000 });
  const correctedWorkoutId = Number(page.url().match(/\/workouts\/(\d+)/)?.[1]);
  await expect(page.getByTestId("workout-saved")).toBeVisible();
  await beat(page, 1400);
  await caption(page, "Done");
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
  await video?.saveAs(outputPath);
  expect(firstWorkoutId).not.toBe(correctedWorkoutId);
}
