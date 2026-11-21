import { memo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

import { cn } from "./cn";

const SAFE_LINK_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

function isSafeHref(href: string | undefined): href is string {
  // Intentionally absolute-only: coach copy has no same-origin link targets,
  // so relative URLs ("/workouts", "#section", "//host/path") fail closed to
  // plain text instead of navigating the app or leaking the origin.
  if (!href) return false;
  try {
    return SAFE_LINK_PROTOCOLS.has(new URL(href).protocol);
  } catch {
    return false;
  }
}

// Raw HTML is never rendered as elements: no rehype plugin is installed, so
// inline HTML in the coach's answer stays inert text instead of becoming
// live DOM nodes.
const markdownComponents: Components = {
  a: ({ href, children }) =>
    isSafeHref(href) ? (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-accent-soft decoration-accent/40 hover:text-accent font-medium underline underline-offset-2 transition-colors"
      >
        {children}
      </a>
    ) : (
      <>{children}</>
    ),
  blockquote: ({ children }) => (
    <blockquote className="border-lab-500 text-ash-300 border-l-2 pl-3 italic">
      {children}
    </blockquote>
  ),
  code: ({ children }) => (
    <code className="num bg-lab-700 text-bone-100 rounded px-1 py-0.5 text-[13px]">
      {children}
    </code>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  h1: ({ children }) => (
    <h1 className="text-bone-100 text-base font-bold leading-snug">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-bone-100 text-base font-bold leading-snug">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-bone-100 text-[15px] font-semibold leading-snug">
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-bone-100 text-[15px] font-semibold leading-snug">
      {children}
    </h4>
  ),
  h5: ({ children }) => (
    <h5 className="text-bone-100 text-[15px] font-semibold leading-snug">
      {children}
    </h5>
  ),
  h6: ({ children }) => (
    <h6 className="text-bone-100 text-[15px] font-semibold leading-snug">
      {children}
    </h6>
  ),
  hr: () => <hr className="border-lab-700" />,
  img: ({ alt }) => (alt ? <span className="text-ash-300">{alt}</span> : null),
  input: ({ checked, disabled }) => (
    <input
      type="checkbox"
      checked={checked ?? false}
      disabled={disabled ?? true}
      className="accent-accent mr-1"
    />
  ),
  li: ({ children }) => <li className="pl-1 [&>p+p]:mt-2">{children}</li>,
  ol: ({ children }) => (
    <ol className="marker:text-ash-300 flex list-decimal flex-col gap-1.5 pl-5">
      {children}
    </ol>
  ),
  pre: ({ children }) => (
    <pre className="rounded-card bg-lab-900 overflow-x-auto p-3 text-[13px] leading-relaxed [&_code]:bg-transparent [&_code]:p-0">
      {children}
    </pre>
  ),
  strong: ({ children }) => (
    <strong className="text-bone-100 font-semibold">{children}</strong>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[14px] leading-relaxed">
        {children}
      </table>
    </div>
  ),
  td: ({ children }) => (
    <td className="border-lab-800 border-b px-2 py-1.5 align-top">
      {children}
    </td>
  ),
  th: ({ children }) => (
    <th className="border-lab-600 text-bone-100 border-b px-2 py-1.5 text-left font-semibold">
      {children}
    </th>
  ),
  ul: ({ children }) => (
    <ul className="marker:text-accent flex list-disc flex-col gap-1.5 pl-5">
      {children}
    </ul>
  ),
};

export interface MarkdownProps {
  content: string;
  className?: string;
}

/**
 * Small, safe markdown renderer for model-generated copy (coach answers now,
 * the live streaming transcript in #14 later). GFM plus single-newline breaks
 * (matching the old whitespace-pre-line behavior) without raw HTML: inline
 * HTML stays inert text, never live elements, and links are limited to
 * http/https/mailto and open in a new tab.
 */
export const Markdown = memo(function Markdown({
  content,
  className,
}: MarkdownProps) {
  return (
    <div
      className={cn(
        "text-bone-300 flex flex-col gap-3 text-[15px] leading-relaxed",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
