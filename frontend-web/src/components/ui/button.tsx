import * as React from "react"
import { createSlot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"

// The focus ring is RED and it is `ring-offset-background`, not a bare ring.
// That offset is load-bearing rather than decorative: the primary button is
// ITSELF red, so a red ring drawn flush against it would be invisible on the
// one control the keyboard lands on most. The page-coloured gap is what makes
// the indicator readable on a red fill and on paper alike.
//
// Every fill below carries an ink measured against it in contrast.test.js.
// The pairing is also the product's danger affordance: a RED fill with INK
// type is the primary action, a CRIMSON fill with WHITE type destroys
// something. Two red buttons, never mistakable, even for someone who reads
// the two hues as one colour.
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-[color,background-color,border-color,box-shadow,transform] duration-200 ease-emphasized focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none active:scale-[0.98] motion-reduce:transition-colors motion-reduce:active:scale-100 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground shadow-soft hover:bg-primary/90 hover:shadow-elevated active:bg-primary",
        destructive:
          "bg-destructive text-destructive-foreground shadow-soft hover:bg-destructive/90 hover:shadow-elevated active:bg-destructive",
        outline:
          "border border-input bg-background shadow-soft hover:border-primary hover:bg-accent hover:text-accent-foreground active:bg-accent",
        secondary:
          "bg-secondary text-secondary-foreground shadow-soft hover:bg-secondary/70 active:bg-secondary",
        ghost: "hover:bg-accent hover:text-accent-foreground active:bg-accent",
        link: "text-primary-emphasis underline-offset-4 hover:underline active:scale-100",
        hero:
          "bg-brand-ink text-brand-2 shadow-floating hover:bg-brand-ink/95 hover:shadow-floating active:bg-brand-ink/90",
        glow:
          "bg-primary text-primary-foreground shadow-elevated hover:-translate-y-0.5 hover:shadow-floating active:translate-y-0 motion-reduce:hover:translate-y-0",
      },
      // The three COMPACT sizes are responsive: 44px below `sm`, their
      // historical desktop height from `sm` up. This is the same shape
      // `Input` (h-11 → sm:h-9), `SelectTrigger` (h-10 → sm:h-9) and the
      // toast close button (h-11 w-11 → sm:h-9 sm:w-9) already use, so the
      // app has ONE rule for touch sizing rather than a second idiom.
      //
      // It is here rather than on the pages because it was already on the
      // pages: roughly forty call sites had each independently bolted a
      // `min-h-11`, an `h-11` or a `size="lg"` onto a button whose only sin
      // was being 36px on a phone. A primitive that every caller has to
      // patch the same way is a primitive with the wrong default. Those
      // overrides are now redundant and some are actively harmful — a bare
      // `min-h-11` pins 44px at EVERY width and defeats the `sm:` step back
      // down, which is why they are listed for removal rather than left.
      //
      // `lg` and `xl` are NOT responsive: they are already 44px and 48px,
      // and they mean "this is a big, deliberate call to action at every
      // width", not "this needs to be tappable".
      size: {
        default: "h-11 px-4 py-2 sm:h-9",
        sm: "h-11 rounded-md px-3 text-xs sm:h-8",
        lg: "h-11 rounded-md px-8 text-base",
        xl: "h-12 rounded-lg px-10 text-base font-semibold",
        icon: "h-11 w-11 sm:h-9 sm:w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

/**
 * `loading` is a prop rather than something each page assembles, because the
 * pages that needed it were each getting a different two thirds of it right.
 * Saving an event spun the Save icon but left the button clickable-looking;
 * other submits swapped in a spinner and dropped the label, so the control
 * changed width mid-click and the next button moved under the cursor. None of
 * them told a screen reader anything at all.
 *
 * One prop, four guarantees: the button is genuinely `disabled` (a second
 * click cannot re-submit), it is `aria-busy` so the state is announced and
 * not merely drawn, the LABEL STAYS so the control keeps its width and the
 * user keeps their reading, and the spinner is `motion-safe` — under
 * prefers-reduced-motion it renders as a static glyph rather than as a
 * near-instant flicker, matching how Skeleton behaves.
 *
 * Ignored under `asChild`: Slot renders a single child element and merges
 * props onto it, so injecting a second element here would throw. A composed
 * trigger that needs a busy state should render <Button loading> directly.
 */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

// Plain `Slot` is typed as `React.HTMLAttributes<HTMLElement>`, which has no
// `disabled`/`form*` members, so spreading `ButtonHTMLAttributes` onto it
// doesn't typecheck. `createSlot` is the same runtime primitive (the default
// `Slot` export is just `createSlot("Slot")`) parameterised for a button.
const ButtonSlot = createSlot<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement>>("Button")

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, loading = false, disabled, children, ...props }, ref) => {
  // Slot renders exactly one child and merges props onto it, so the loading
  // branch must not hand it a two-element array — not even `[false, child]`,
  // which is what `{busy && <Loader2/>}` produces when busy is false. The
  // asChild path therefore returns before any of that.
  if (asChild) {
    return (
      <ButtonSlot className={cn(buttonVariants({ variant, size, className }))} ref={ref} disabled={disabled} {...props}>
        {children}
      </ButtonSlot>
    );
  }
  return (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Loader2 className="motion-safe:animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
})
Button.displayName = "Button"

export { Button, buttonVariants }
