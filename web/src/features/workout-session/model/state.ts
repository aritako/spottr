export type SaveWorkoutState =
  | { status: "idle" }
  | { status: "success"; workoutId: number }
  | { status: "error"; message: string };

export const initialSaveState: SaveWorkoutState = { status: "idle" };

export type DeleteWorkoutState =
  | { status: "idle" }
  | { status: "success" }
  | { status: "error"; message: string };

export const initialDeleteState: DeleteWorkoutState = { status: "idle" };
