export type Unit = "kg" | "lbs";

export type ExerciseCategory =
  | "squat"
  | "hinge"
  | "lunge"
  | "horizontal_push"
  | "vertical_push"
  | "horizontal_pull"
  | "vertical_pull"
  | "carry"
  | "isolation"
  | "core";

export interface Exercise {
  id: number;
  name: string;
  category: ExerciseCategory | null;
  is_compound: boolean;
}

export interface CreateExerciseInput {
  name: string;
  category?: ExerciseCategory | null;
  is_compound?: boolean;
}

export interface SetRead {
  id: number;
  exercise_id: number;
  weight: number;
  reps: number;
  rpe: number | null;
  set_index: number;
}

export interface CreateSetInput {
  exercise_id: number;
  weight: number;
  reps: number;
  rpe?: number | null;
  set_index?: number | null;
}

export interface Workout {
  id: number;
  unit: Unit;
  bodyweight: number | null;
  notes: string | null;
  performed_at: string;
  created_at: string;
  sets: SetRead[];
}

export interface CreateWorkoutInput {
  unit: Unit;
  bodyweight?: number | null;
  notes?: string | null;
  performed_at: string;
  sets: CreateSetInput[];
}

export interface Citation {
  document: string;
  chunk_index: number;
}

export interface AskCoachResponse {
  answer: string;
  used_tools: string[];
  citations: Citation[];
}

export interface PaginationParams {
  /** Zero-based page index. */
  page?: number;
  /** 1–100, defaults to 10 on the API. */
  pageSize?: number;
}

export interface EntityCreated {
  id: number;
}
