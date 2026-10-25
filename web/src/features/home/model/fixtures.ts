/**
 * Temporary fixture data for the home screen.
 *
 * The API does not expose a "next workout", weekly summary or coach nudge yet.
 * Replace this module screen-by-screen as those endpoints land.
 */

export interface HomeFixtures {
  nextWorkout: {
    slug: string;
    name: string;
    exerciseCount: number;
    minutes: number;
    lastDone: string;
  };
  week: {
    completedSessions: number;
    totalSessions: number;
    completedDays: number[];
    prDay: number;
    plannedDays: number[];
  };
  coachNudge: {
    text: string;
    citation: string;
  };
}

export const homeFixtures: HomeFixtures = {
  nextWorkout: {
    slug: "pull-a",
    name: "Pull A",
    exerciseCount: 5,
    minutes: 55,
    lastDone: "Fri 16 Oct",
  },
  week: {
    completedSessions: 2,
    totalSessions: 4,
    completedDays: [0, 2],
    prDay: 2,
    plannedDays: [3, 4],
  },
  coachNudge: {
    text: "Your deadlift has been 140 × 5 two sessions running. Go for a sixth rep today",
    citation: "Last two deadlift sessions",
  },
};
