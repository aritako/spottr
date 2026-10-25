import type { ReactNode } from "react";

import { Card } from "./card";

export interface EmptyStateProps {
  eyebrow: string;
  title: string;
  body: string;
  icon?: ReactNode;
  children?: ReactNode;
}

export function EmptyState({
  eyebrow,
  title,
  body,
  icon,
  children,
}: EmptyStateProps) {
  return (
    <Card className="rounded-panel flex flex-col items-start gap-4 p-6">
      {icon ? <div className="text-accent">{icon}</div> : null}
      <div className="flex flex-col gap-2">
        <span className="eyebrow">{eyebrow}</span>
        <h2 className="display text-2xl leading-none">{title}</h2>
        <p className="text-bone-300 max-w-prose text-sm leading-relaxed">
          {body}
        </p>
      </div>
      {children}
    </Card>
  );
}
