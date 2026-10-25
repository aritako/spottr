/**
 * Query keys for workout history.
 *
 * Keys live in the slice so that reads and invalidations cannot drift apart.
 * The first consumer is the history screen; it will call `listWorkouts` through
 * these keys once the session rows are wired.
 */
export const workoutKeys = {
  all: ["workouts"] as const,
  lists: () => [...workoutKeys.all, "list"] as const,
  list: (page: number, pageSize: number) =>
    [...workoutKeys.lists(), { page, pageSize }] as const,
};
