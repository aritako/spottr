"use client";

import { useActionState, useEffect, useState, type FormEvent } from "react";

import {
  BrandMark,
  Button,
  ChevronRightIcon,
  Citation,
  PlusIcon,
  SendIcon,
  cn,
} from "@spottr/ui";

import { coachStats, coachSuggestions } from "~/lib/fixtures";
import { MAX_QUESTION_LENGTH } from "~/lib/coach";
import { readStringField } from "~/lib/form-value";

import { askCoach, type CoachState } from "./actions";

const initialCoachState: CoachState = { status: "idle" };

function StartState({ disabled }: { disabled: boolean }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 px-1">
        <BrandMark className="size-11" />
        <h2 className="text-xl leading-snug font-semibold tracking-[-0.01em]">
          Ask anything about your training.
        </h2>
        <p className="text-sm leading-relaxed text-bone-300">
          Answers come from your own log, with the sessions they&apos;re based
          on.
        </p>
      </div>

      <div className="grid grid-cols-3 rounded-[18px] bg-lab-800 py-3">
        {coachStats.map((stat, index) => (
          <div
            key={stat.label}
            className={cn(
              "flex flex-col items-center gap-1",
              index > 0 && "border-l border-lab-600",
            )}
          >
            <span className="num text-[15px]">{stat.value}</span>
            <span className="eyebrow text-[8.5px]">{stat.label}</span>
          </div>
        ))}
      </div>

      <p className="px-1 text-[11px] leading-relaxed text-ash-500">
        Session counts are preview data. Coach answers use your real log.
      </p>

      <div className="flex flex-col gap-2">
        <span className="eyebrow px-1">Try asking</span>
        {coachSuggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="submit"
            name="suggestion"
            value={suggestion}
            disabled={disabled}
            className="flex h-[52px] w-full items-center justify-between rounded-2xl bg-lab-800 px-4 text-left text-sm text-bone-100 transition-colors hover:bg-lab-850 disabled:opacity-50"
          >
            {suggestion}
            <ChevronRightIcon className="size-3.5 text-ash-300" />
          </button>
        ))}
      </div>
    </div>
  );
}

function Answer({
  state,
}: {
  state: Extract<CoachState, { status: "answer" }>;
}) {
  const { citations, used_tools: usedTools } = state.response;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-[15px] leading-relaxed whitespace-pre-line text-bone-300">
        {state.response.answer}
      </p>

      {citations.length > 0 ? (
        <div className="flex flex-col gap-2">
          <span className="eyebrow">Sources · {citations.length}</span>
          <div className="flex flex-wrap gap-1.5">
            {citations.map((citation, index) => (
              <span
                key={`${citation.document}-${citation.chunk_index}`}
                title={`${citation.document} · chunk ${citation.chunk_index + 1}`}
                className="flex h-8 max-w-full items-center gap-2 rounded-full bg-lab-800 px-3 text-[11px] ring-1 ring-lab-600 ring-inset"
              >
                <Citation
                  index={index + 1}
                  title={citation.document}
                  className="align-[0]"
                />
                <span className="max-w-[13rem] truncate">
                  {citation.document}
                </span>
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {usedTools.length > 0 ? (
        <span className="num text-[10px] text-ash-500">
          tools · {usedTools.join(", ")}
        </span>
      ) : null}
    </div>
  );
}

function Composer({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <input
          name="question"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask about your training"
          aria-label="Message coach"
          autoComplete="off"
          maxLength={MAX_QUESTION_LENGTH}
          disabled={disabled}
          className="h-[46px] min-w-0 flex-1 rounded-full bg-lab-800 px-[18px] text-[15px] shadow-[inset_0_0_0_1px_#2F2727] placeholder:text-ash-500 focus:shadow-[inset_0_0_0_1.5px_#F0524A] focus:outline-none disabled:opacity-60"
        />
        <Button
          type="submit"
          size="icon"
          aria-label="Send"
          disabled={disabled || value.trim().length === 0}
          className="size-[46px] shrink-0"
        >
          {disabled ? (
            <span
              aria-hidden="true"
              className="size-4 animate-spin rounded-full border-2 border-accent-ink/30 border-t-accent-ink"
            />
          ) : (
            <SendIcon className="size-[18px]" />
          )}
        </Button>
      </div>
      <p className="text-ash-500 text-center text-[10px] leading-relaxed">
        AI can be wrong · Not medical advice · Workout data is sent to OpenAI
      </p>
    </div>
  );
}

function CoachPanel() {
  const [state, formAction, isPending] = useActionState(
    askCoach,
    initialCoachState,
  );
  const [question, setQuestion] = useState("");
  const [submittedQuestion, setSubmittedQuestion] = useState("");

  useEffect(() => {
    if (state.status !== "idle") setQuestion("");
  }, [state]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    const data = new FormData(event.currentTarget);
    setSubmittedQuestion(readStringField(data, "suggestion", "question"));
  }

  const activeQuestion = isPending
    ? submittedQuestion
    : state.status === "idle"
      ? ""
      : state.question;

  return (
    <form
      action={formAction}
      onSubmit={handleSubmit}
      className="flex flex-1 flex-col gap-5"
    >
      {!isPending && state.status === "idle" ? (
        <StartState disabled={isPending} />
      ) : null}

      {activeQuestion ? (
        <div className="flex justify-end">
          <p className="max-w-[85%] rounded-[20px] rounded-br-md bg-lab-700 px-4 py-2.5 text-[15px]">
            {activeQuestion}
          </p>
        </div>
      ) : null}

      {isPending ? (
        <div
          className="flex items-center gap-2 px-1 text-sm text-ash-300"
          role="status"
        >
          <span className="flex gap-1" aria-hidden="true">
            <span className="size-1.5 animate-pulse rounded-full bg-accent" />
            <span className="size-1.5 animate-pulse rounded-full bg-accent [animation-delay:150ms]" />
            <span className="size-1.5 animate-pulse rounded-full bg-accent [animation-delay:300ms]" />
          </span>
          Reading your log…
        </div>
      ) : null}

      {!isPending && state.status === "answer" ? <Answer state={state} /> : null}

      {!isPending && state.status === "error" ? (
        <div
          role="alert"
          className="flex flex-col gap-2 rounded-card bg-accent/5 p-4 ring-1 ring-accent/30 ring-inset"
        >
          <span className="eyebrow text-accent">Coach unavailable</span>
          <p className="text-sm leading-relaxed text-bone-300">
            {state.message}
          </p>
        </div>
      ) : null}

      <div className="sticky bottom-[calc(env(safe-area-inset-bottom)+88px)] z-30 mt-auto -mx-1 bg-lab-900/95 px-1 py-2 backdrop-blur-md lg:static lg:mx-0 lg:bg-transparent lg:p-0">
        <Composer value={question} onChange={setQuestion} disabled={isPending} />
      </div>
    </form>
  );
}

export function CoachScreen() {
  const [session, setSession] = useState(0);

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-9.5rem)] w-full max-w-2xl flex-col gap-4 lg:min-h-[calc(100dvh-5rem)]">
      <header className="flex items-start justify-between gap-4 pb-2">
        <div className="flex flex-col gap-2">
          <span className="eyebrow">Training intelligence</span>
          <h1 className="display text-[22px] leading-none lg:text-[28px]">
            Coach
          </h1>
        </div>
        <Button
          variant="secondary"
          size="icon"
          aria-label="New conversation"
          title="New conversation"
          onClick={() => setSession((current) => current + 1)}
        >
          <PlusIcon className="size-4" />
        </Button>
      </header>

      {/* Remounting the panel resets useActionState cleanly. */}
      <CoachPanel key={session} />
    </div>
  );
}
