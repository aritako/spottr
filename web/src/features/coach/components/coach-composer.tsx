import { Button, SendIcon } from "~/components/ui";

import { MAX_QUESTION_LENGTH } from "../model/constants";

export function CoachComposer({
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
          className="bg-lab-800 placeholder:text-ash-500 h-[46px] min-w-0 flex-1 rounded-full px-[18px] text-[15px] shadow-[inset_0_0_0_1px_#2F2727] focus:shadow-[inset_0_0_0_1.5px_#F0524A] focus:outline-none disabled:opacity-60"
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
              className="border-accent-ink/30 border-t-accent-ink size-4 animate-spin rounded-full border-2"
            />
          ) : (
            <SendIcon className="size-[18px]" />
          )}
        </Button>
      </div>
      <p className="text-ash-500 text-center text-[10px] leading-relaxed">
        AI can be wrong · Not medical advice · Workout data is sent to your AI
        provider
      </p>
    </div>
  );
}
