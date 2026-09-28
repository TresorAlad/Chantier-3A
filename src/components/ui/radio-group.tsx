import * as React from "react"
import * as RadioGroupPrimitive from "@radix-ui/react-radio-group"
import { cn } from "@/lib/utils"
import { DotFilledIcon } from "@radix-ui/react-icons"

const RadioGroup = React.forwardRef<
  React.ElementRef<typeof RadioGroupPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Root>
>(({ className, ...props }, ref) => {
  return (<RadioGroupPrimitive.Root className={cn("grid gap-2", className)} {...props} ref={ref} />);
})
RadioGroup.displayName = RadioGroupPrimitive.Root.displayName

// Same 16px-dot / 24px-target split as Checkbox, via the same single
// `hit-area-24` utility, and for the same reason: WCAG 2.5.8 sizes the
// TARGET, not the artwork. See checkbox.tsx for the full argument — the
// short version is that the expander is pinned at exactly 24x24 because a
// bigger one would start stealing taps from the next radio in the stack,
// and `m-1` reserves that 24px of pitch in layout so the group's spacing
// cannot fall below it.
//
// A radio group is the harder case of the two: checkboxes usually appear one
// at a time next to a sentence, whereas radios are stacked BY DEFINITION, so
// the neighbour whose tap could be stolen is always present. RadioGroup's
// own `gap-2` puts 8px between rows on top of the margins, but the guarantee
// does not rest on that gap — a caller may override it to `gap-0` and the
// centres are still 24px apart, because the margins alone supply it.
const RadioGroupItem = React.forwardRef<
  React.ElementRef<typeof RadioGroupPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Item>
>(({ className, ...props }, ref) => {
  return (
    (<RadioGroupPrimitive.Item
      ref={ref}
      className={cn(
        "hit-area-24 m-1 aspect-square h-4 w-4 rounded-full border border-primary text-primary-emphasis shadow-soft transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}>
      <RadioGroupPrimitive.Indicator className="flex items-center justify-center">
        <DotFilledIcon className="h-3.5 w-3.5 fill-primary" />
      </RadioGroupPrimitive.Indicator>
    </RadioGroupPrimitive.Item>)
  );
})
RadioGroupItem.displayName = RadioGroupPrimitive.Item.displayName

export { RadioGroup, RadioGroupItem }
