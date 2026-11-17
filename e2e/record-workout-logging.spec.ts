import { test } from "@playwright/test";

import {
  DESKTOP,
  DESKTOP_RECORDING_PATH,
  recordFlow,
  videoOptions,
} from "./workout-logging-recording";

test.use({ viewport: DESKTOP, video: videoOptions(DESKTOP) });

test("record the workout logging flow", async ({ page, request }) => {
  await recordFlow(page, request, DESKTOP_RECORDING_PATH);
});
