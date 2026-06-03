import { Slot } from "@radix-ui/react-slot";
import { type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean;
  variant?: "primary" | "secondary" | "ghost";
};

export function Button({ asChild, className, variant = "primary", ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      className={cn(
        "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-50",
        variant === "primary" && "bg-cyan-400 text-slate-950 hover:bg-cyan-300 focus-visible:outline-cyan-300",
        variant === "secondary" && "bg-slate-800 text-slate-100 hover:bg-slate-700 focus-visible:outline-slate-500",
        variant === "ghost" && "text-slate-300 hover:bg-slate-900 hover:text-white focus-visible:outline-slate-500",
        className
      )}
      {...props}
    />
  );
}
