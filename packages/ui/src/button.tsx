import type { ButtonHTMLAttributes } from "react";

import { cn } from "./cn";

export type ButtonVariant = "primary" | "secondary" | "outline" | "ghost";
export type ButtonSize = "sm" | "md" | "lg" | "icon";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "display rounded-full bg-accent text-accent-ink tracking-[0.1em] hover:bg-accent-soft",
  secondary: "rounded-full bg-lab-700 text-bone-100 hover:bg-lab-600",
  outline:
    "rounded-full text-bone-100 ring-1 ring-inset ring-lab-600 hover:bg-lab-800",
  ghost: "rounded-full text-ash-300 hover:text-bone-100",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-9 px-4 text-[11px]",
  md: "h-11 px-5 text-[12px]",
  lg: "h-[52px] px-6 text-[13px]",
  icon: "size-11 p-0",
};

export interface ButtonClassOptions {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  className?: string;
}

/** Shared classes so links can look like buttons without a polymorphic component. */
export function buttonClasses({
  variant = "primary",
  size = "md",
  fullWidth = false,
  className,
}: ButtonClassOptions = {}): string {
  return cn(
    "inline-flex items-center justify-center gap-2 transition-colors disabled:pointer-events-none disabled:opacity-50",
    variantClasses[variant],
    sizeClasses[size],
    fullWidth && "w-full",
    className,
  );
}

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>, ButtonClassOptions {}

export function Button({
  className,
  variant,
  size,
  fullWidth,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={buttonClasses({ variant, size, fullWidth, className })}
      {...props}
    />
  );
}
