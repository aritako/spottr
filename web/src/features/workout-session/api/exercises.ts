import { createAppClient, type Exercise } from "@spottr/api-client";

import { env } from "~/env";

const PAGE_SIZE = 8;
const MAX_PAGES = 50;

/** Load the full exercise catalog, paging until a short page. */
export async function loadExerciseCatalog(): Promise<Exercise[]> {
  const client = createAppClient({ baseUrl: env.SPOTTR_API_URL });
  const catalog: Exercise[] = [];

  for (let page = 0; page < MAX_PAGES; page += 1) {
    const chunk = await client.listExercises({ page, pageSize: PAGE_SIZE });
    catalog.push(...chunk);
    if (chunk.length < PAGE_SIZE) break;
  }

  return catalog;
}
