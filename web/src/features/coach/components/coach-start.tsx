import { BrandMark, ChevronRightIcon, cn } from "~/components/ui";

import { coachStats, coachSuggestions } from "../model/fixtures";

export function CoachStart({ disabled }: { disabled: boolean }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3 px-1">
        <BrandMark className="size-11" />
        <h2 className="text-xl font-semibold leading-snug tracking-[-0.01em]">
          Ask anything about your training.
        </h2>
        <p className="text-bone-300 text-sm leading-relaxed">
          Answers come from your own log, with the sessions they&apos;re based
          on.
        </p>
      </div>

      <div className="bg-lab-800 grid grid-cols-3 rounded-[18px] py-3">
        {coachStats.map((stat, index) => (
          <div
            key={stat.label}
            className={cn(
              "flex flex-col items-center gap-1",
              index > 0 && "border-lab-600 border-l",
            )}
          >
            <span className="num text-[15px]">{stat.value}</span>
            <span className="eyebrow text-[8.5px]">{stat.label}</span>
          </div>
        ))}
      </div>

      <p className="text-ash-500 px-1 text-[11px] leading-relaxed">
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
            className="bg-lab-800 text-bone-100 hover:bg-lab-850 flex h-[52px] w-full items-center justify-between rounded-2xl px-4 text-left text-sm transition-colors disabled:opacity-50"
          >
            {suggestion}
            <ChevronRightIcon className="text-ash-300 size-3.5" />
          </button>
        ))}
      </div>
    </div>
  );
}
