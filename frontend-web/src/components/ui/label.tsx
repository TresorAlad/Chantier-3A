import * as React from "react"
import * as LabelPrimitive from "@radix-ui/react-label"
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils"

// Measured at 390px AND 1440px on the sign-in form: 34x17 and 61x17.
//
// A <label> IS an activation target — tapping it focuses the field it names —
// so it is subject to WCAG 2.5.8, which asks for 24x24 CSS px. At 17px tall
// every label in the product was under it.
//
// It is deliberately taken to 24 and not to 44, and the reason is worth
// stating rather than leaving as a number for somebody to later "fix".
// Reaching 44 means 13px of padding above and below every label in the app,
// which adds 26px to every field: a six-field form grows by 156px, and on the
// 390px phone this is all for, that pushes the submit button off the first
// screen of every form in the product. WCAG 2.5.5's 44px is AAA and carries
// an explicit "Equivalent" exception — it does not apply to a control whose
// function is also available through an adjacent target that DOES meet the
// size. Here that adjacent target is the field itself, which `input.tsx`
// takes to 44px below sm precisely so this exception is real rather than
// asserted. Growing the label instead would trade a genuine 44px target for
// a redundant one and a longer scroll.
//
// `inline-flex items-center` with `leading-tight` rather than `leading-none`:
// the box grows around the text instead of the text moving, so no label
// shifts off its baseline and no form re-flows.
//
// Fixed here rather than in form.tsx's FormLabel, which is where it was first
// reported: FormLabel is only the react-hook-form path, and the form that was
// measured — sign-in — reaches for <Label> directly, as do 17 call sites.
// Fixing the wrapper would have left the primitive short and the report
// looking addressed.
const labelVariants = cva(
  "inline-flex min-h-[24px] items-center text-sm font-medium leading-tight peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
)

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root ref={ref} className={cn(labelVariants(), className)} {...props} />
))
Label.displayName = LabelPrimitive.Root.displayName

export { Label }
