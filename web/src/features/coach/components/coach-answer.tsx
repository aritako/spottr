import { Citation } from "~/components/ui";

import type { CoachState } from "../model/state";

export function CoachAnswer({
  state,
}: {
  state: Extract<CoachState, { status: "answer" }>;
}) {
  const { citations, used_tools: usedTools } = state.response;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-bone-300 whitespace-pre-line text-[15px] leading-relaxed">
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
                className="bg-lab-800 ring-lab-600 flex h-8 max-w-full items-center gap-2 rounded-full px-3 text-[11px] ring-1 ring-inset"
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
        <span className="num text-ash-500 text-[10px]">
          tools · {usedTools.join(", ")}
        </span>
      ) : null}
    </div>
  );
}
