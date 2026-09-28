import * as React from "react"
import * as SeparatorPrimitive from "@radix-ui/react-separator"

import { cn } from "@/lib/utils"

export interface SeparatorProps extends React.ComponentPropsWithoutRef<typeof SeparatorPrimitive.Root> {
  variant?: "line" | "perforated";
}

const Separator = React.forwardRef<React.ElementRef<typeof SeparatorPrimitive.Root>, SeparatorProps>((
  { className, orientation = "horizontal", decorative = true, variant = "line", ...props },
  ref
) => (
  <SeparatorPrimitive.Root
    ref={ref}
    decorative={decorative}
    orientation={orientation}
    className={cn(
      "shrink-0",
      variant === "perforated"
        ? [
            "bg-transparent",
            orientation === "horizontal"
              ? "h-0 w-full border-t border-dashed border-primary/30"
              : "h-full w-0 border-l border-dashed border-primary/30",
          ]
        : [
            "bg-border",
            orientation === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]",
          ],
      className
    )}
    {...props} />
))
Separator.displayName = SeparatorPrimitive.Root.displayName

export { Separator }
