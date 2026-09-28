import * as React from 'react';
import * as CheckboxPrimitive from '@radix-ui/react-checkbox';
import { CheckIcon } from '@radix-ui/react-icons';

import { cn } from '@/lib/utils';

// The BOX is 16px. The TARGET is 24px. Those are two different things and
// only the second one is a WCAG 2.5.8 (Target Size, Minimum, AA) obligation,
// so the fix is `hit-area-24` — a transparent 24x24 pseudo-element, defined
// once in tailwind.config.js — rather than a bigger tick. A 24px checkbox
// beside 14px label text looks like a bug, and growing the visual box would
// have rippled through every form that lines a checkbox up with a line of
// type.
//
// TWO RULES MAKE THE EXPANDER SAFE, AND THEY ONLY WORK TOGETHER:
//
//  1. It is EXACTLY 24x24 (enforced by the utility, not by each caller).
//     Not `-inset-2`, not "as big as it can get". An oversized hit area is
//     not a better hit area: past the point where two neighbouring targets'
//     areas meet, a tap near the boundary starts landing on the WRONG
//     control, which is worse than the small target it was meant to fix.
//     24 is the standard's floor and also the largest value that is safe
//     here — see rule 2.
//
//  2. `m-1` reserves the expander's own overhang in LAYOUT. This is the part
//     that turns "probably fine" into a guarantee. 4px of margin on every
//     side means two of these controls, adjacent in any direction, always
//     have at least 8px between their border boxes, so their centres are at
//     least 16 + 8 = 24px apart — exactly the pitch at which two 24px areas
//     abut without overlapping. It holds at gap-0, which is the tightest
//     stack a caller can build, so no caller can stack them tightly enough
//     to break it. Margins would defeat this if they collapsed, but Radix
//     renders the Root as a <button> (inline-level, non-collapsing) and flex
//     and grid containers never collapse margins either.
//
// Proven by hit-testing rather than by argument: a fixture stacks these at
// gap-0, gap-1 and gap-2, vertically and horizontally, and asserts via
// document.elementFromPoint that each control's centre AND all four expanded
// edges resolve to that control and never to its neighbour.
//
// The one case the primitive cannot speak for is a checkbox set flush
// against a DIFFERENT kind of control; `m-1` guarantees spacing against
// another checkbox, not against an arbitrary neighbour with no margin of
// its own.
const Checkbox = React.forwardRef<
    React.ElementRef<typeof CheckboxPrimitive.Root>,
    React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>
>(({ className, ...props }, ref) => (
    <CheckboxPrimitive.Root
        ref={ref}
        className={cn(
            'peer hit-area-24 m-1 h-4 w-4 shrink-0 rounded-sm border border-primary shadow-soft transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground',
            className,
        )}
        {...props}>
        <CheckboxPrimitive.Indicator className={cn('flex items-center justify-center text-current')}>
            <CheckIcon className='h-4 w-4' />
        </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
));
Checkbox.displayName = CheckboxPrimitive.Root.displayName;

export { Checkbox };
