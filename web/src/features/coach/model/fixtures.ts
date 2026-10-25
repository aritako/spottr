/**
 * Temporary preview data for the coach start screen.
 *
 * Session counts are not exposed by the API yet. Suggestions are copy, not
 * data, but they live here so the start screen has no cross-slice imports.
 */

export const coachSuggestions = [
  "Has my bench stalled?",
  "Which lift is progressing fastest?",
  "Am I training legs enough?",
  "Plan my next 4 weeks",
] as const;

export const coachStats = [
  { label: "Sessions", value: "47" },
  { label: "Sets", value: "1,312" },
  { label: "Since", value: "3 Mar" },
] as const;
