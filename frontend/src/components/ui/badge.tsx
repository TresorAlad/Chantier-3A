import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils"

// text-xs is 12px — the suite's type floor, and a badge is the component most
// likely to be shrunk below it by someone chasing a dense row. It is pinned
// here rather than left to the caller.
//
// `accent` is the quiet one: the red WASH under deep red type, for a label
// that should read as brand without shouting like a filled `default` badge.
const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md border px-2.5 py-0.5 text-xs font-semibold leading-5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background [&_svg]:size-3 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow-soft hover:bg-primary/90",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/70",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow-soft hover:bg-destructive/90",
        success:
          "border-transparent bg-success text-success-foreground shadow-soft hover:bg-success/90",
        warning:
          "border-transparent bg-warning text-warning-foreground shadow-soft hover:bg-warning/90",
        accent: "border-transparent bg-accent text-accent-foreground hover:bg-accent/70",
        outline: "border-border text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({
  className,
  variant,
  ...props
}: BadgeProps) {
  return (<div className={cn(badgeVariants({ variant }), className)} {...props} />);
}

export { Badge, badgeVariants }
