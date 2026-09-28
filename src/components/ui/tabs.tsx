import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"

import { cn } from "@/lib/utils"

const Tabs = TabsPrimitive.Root

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      // max-w-full + overflow-x-auto keeps a long tab set from being the one
      // thing that makes a 390px page scroll sideways; no-scrollbar hides the
      // bar itself so the strip still reads as chrome rather than as content.
      // No fixed height here on purpose: the list hugs whatever height its
      // triggers need (their own `h-11 sm:h-9`, see TabsTrigger) plus this
      // padding, so the pill chrome and the touch target always agree — a
      // fixed height here previously let a 32px trigger sit inside a 36px
      // box and never grow to the 44px floor at sm's mobile breakpoint.
      "inline-flex max-w-full items-center justify-start overflow-x-auto rounded-lg bg-muted p-1 text-muted-foreground no-scrollbar",
      className
    )}
    {...props} />
))
TabsList.displayName = TabsPrimitive.List.displayName

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      // The active tab is named in brand INK (--primary-emphasis, AA on every
      // surface a tab strip sits on) rather than in the brand FILL, which
      // would be 3.34:1 at this size. Colour is not the only signal either:
      // the active tab also lifts onto the page ground with a shadow.
      // h-11 below sm, h-9 from sm up — the same house idiom Button and
      // Input use (see input.tsx): a tab is a real touch target, and this
      // was previously sized only by its own padding + line-height (32px at
      // every breakpoint), the one remaining sub-44px target in the app.
      "inline-flex h-11 shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium ring-offset-background transition-all duration-150 ease-emphasized hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-primary-emphasis data-[state=active]:shadow-soft sm:h-9",
      className
    )}
    {...props} />
))
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      className
    )}
    {...props} />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }
