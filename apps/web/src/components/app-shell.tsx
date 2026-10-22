import Link from "next/link";

import { Logo } from "@spottr/ui";

import { AppNav } from "./app-nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-lab-900 min-h-dvh lg:flex">
      <aside className="border-lab-800 sticky top-0 hidden h-dvh w-[224px] shrink-0 flex-col border-r px-4 py-6 lg:flex">
        <Link
          href="/"
          aria-label="Spottr home"
          className="mb-8 px-3.5 focus-visible:rounded-md"
        >
          <Logo className="text-[19px]" />
        </Link>

        <AppNav variant="sidebar" />

        <div className="mt-auto flex items-center gap-3 px-3.5 py-2">
          <span
            aria-hidden="true"
            className="bg-lab-700 flex size-8 items-center justify-center rounded-full text-[13px] font-semibold"
          >
            M
          </span>
          <span className="text-bone-300 text-sm">Melo</span>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col lg:min-h-dvh">
        <div className="mx-auto w-full max-w-[1180px] flex-1 px-4 pb-32 pt-5 sm:px-6 lg:px-10 lg:pb-10 lg:pt-8">
          {children}
        </div>
      </div>

      <div className="bg-lab-900/95 fixed inset-x-0 bottom-0 z-40 px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur-md lg:hidden">
        <AppNav variant="bottom" />
      </div>
    </div>
  );
}
