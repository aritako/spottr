import { Logo, cn } from "~/components/ui";

export interface PageHeaderProps {
  eyebrow: string;
  title: string;
  showLogo?: boolean;
  action?: React.ReactNode;
}

export function PageHeader({
  eyebrow,
  title,
  showLogo = false,
  action,
}: PageHeaderProps) {
  return (
    <header className="flex items-start justify-between gap-4 pb-6">
      <div className="flex flex-col gap-2">
        <span className="eyebrow">{eyebrow}</span>
        <div className="flex items-baseline gap-3">
          {showLogo ? <Logo className="text-[22px] lg:hidden" /> : null}
          <h1
            className={cn(
              "display text-[22px] leading-none lg:text-[28px]",
              showLogo && "sr-only lg:not-sr-only",
            )}
          >
            {title}
          </h1>
        </div>
      </div>
      {action}
    </header>
  );
}
