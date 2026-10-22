"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  BarbellIcon,
  CoachIcon,
  HistoryIcon,
  ProgressIcon,
  cn,
} from "@spottr/ui";

const items = [
  { href: "/", label: "Workout", icon: BarbellIcon },
  { href: "/history", label: "History", icon: HistoryIcon },
  { href: "/coach", label: "Coach", icon: CoachIcon },
  { href: "/progress", label: "Progress", icon: ProgressIcon },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/") {
    return (
      pathname === "/" ||
      pathname.startsWith("/workouts") ||
      pathname.startsWith("/routines")
    );
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppNav({ variant }: { variant: "bottom" | "sidebar" }) {
  const pathname = usePathname();

  if (variant === "sidebar") {
    return (
      <nav aria-label="Primary" className="flex flex-col gap-1">
        {items.map(({ href, label, icon: Icon }) => {
          const active = isActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex h-11 items-center gap-3 rounded-[14px] px-3.5 text-sm font-medium transition-colors",
                active
                  ? "bg-lab-800 text-bone-100"
                  : "text-ash-300 hover:bg-lab-850 hover:text-bone-100",
              )}
            >
              <Icon className={cn("size-[18px]", active && "text-accent")} />
              {label}
            </Link>
          );
        })}
      </nav>
    );
  }

  return (
    <nav
      aria-label="Primary"
      className="bg-lab-800 flex h-16 items-center justify-around rounded-3xl shadow-[0_0_0_1px_#2F2727]"
    >
      {items.map(({ href, label, icon: Icon }) => {
        const active = isActive(pathname, href);
        return (
          <Link
            key={href}
            href={href}
            aria-label={label}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex size-14 flex-col items-center justify-center gap-1 rounded-2xl transition-colors",
              active
                ? "bg-lab-700 text-bone-100"
                : "text-ash-300 hover:text-bone-100",
            )}
          >
            <Icon className="size-[22px]" />
            <span
              className={cn(
                "size-1 rounded-full",
                active ? "bg-accent" : "bg-transparent",
              )}
            />
          </Link>
        );
      })}
    </nav>
  );
}
