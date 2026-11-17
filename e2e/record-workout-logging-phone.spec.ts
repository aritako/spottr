import { test } from "@playwright/test";

import {
  MOBILE,
  MOBILE_RECORDING_PATH,
  recordFlow,
  videoOptions,
} from "./workout-logging-recording";

test.use({ viewport: MOBILE, video: videoOptions(MOBILE) });

test("record the workout logging flow on a phone screen", async ({
  page,
  request,
}) => {
  await recordFlow(page, request, MOBILE_RECORDING_PATH);
});
