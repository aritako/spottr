"use client";

import { useActionState, useEffect, useState, type FormEvent } from "react";

import { Button, PlusIcon } from "~/components/ui";
import { readStringField } from "~/lib/form-value";

import { askCoach } from "../actions";
import { initialCoachState } from "../model/state";
import { CoachAnswer } from "./coach-answer";
import { CoachComposer } from "./coach-composer";
import { CoachStart } from "./coach-start";

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
        <CoachStart disabled={isPending} />
      ) : null}

      {activeQuestion ? (
        <div className="flex justify-end">
          <p className="bg-lab-700 max-w-[85%] rounded-[20px] rounded-br-md px-4 py-2.5 text-[15px]">
            {activeQuestion}
          </p>
        </div>
      ) : null}

      {isPending ? (
        <div
          className="text-ash-300 flex items-center gap-2 px-1 text-sm"
          role="status"
        >
          <span className="flex gap-1" aria-hidden="true">
            <span className="bg-accent size-1.5 animate-pulse rounded-full" />
            <span className="bg-accent size-1.5 animate-pulse rounded-full [animation-delay:150ms]" />
            <span className="bg-accent size-1.5 animate-pulse rounded-full [animation-delay:300ms]" />
          </span>
          Reading your log…
        </div>
      ) : null}

      {!isPending && state.status === "answer" ? (
        <CoachAnswer state={state} />
      ) : null}

      {!isPending && state.status === "error" ? (
        <div
          role="alert"
          className="rounded-card bg-accent/5 ring-accent/30 flex flex-col gap-2 p-4 ring-1 ring-inset"
        >
          <span className="eyebrow text-accent">Coach unavailable</span>
          <p className="text-bone-300 text-sm leading-relaxed">
            {state.message}
          </p>
        </div>
      ) : null}

      <div className="bg-lab-900/95 sticky bottom-[calc(env(safe-area-inset-bottom)+88px)] z-30 -mx-1 mt-auto px-1 py-2 backdrop-blur-md lg:static lg:mx-0 lg:bg-transparent lg:p-0">
        <CoachComposer
          value={question}
          onChange={setQuestion}
          disabled={isPending}
        />
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
