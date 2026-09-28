import * as React from 'react';

import { cn } from '@/lib/utils';

/**
 * Card is the app's raised surface: a bordered, rounded panel on `--card`.
 *
 * `interactive` is for a card that is itself the control — a whole tile you
 * click to open an event. It is a prop rather than a class every caller
 * assembles because the two call sites that needed it had already drifted
 * apart: one used `hover:-translate-y-1 hover:shadow-xl`, the other
 * `hover:shadow-md`, and neither `shadow-xl` nor `shadow-md` is a step on
 * this product's elevation ramp (`soft` / `elevated` / `floating`, defined
 * per theme in index.css). It also carries the parts that are easy to forget
 * and impossible to see: a focus-visible ring, so the tile is reachable by
 * keyboard at all, and `motion-reduce`, so the lift is not forced on someone
 * who asked for no motion.
 *
 * @param {object} props
 * @param {boolean} [props.interactive] the whole card is a control
 */
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    interactive?: boolean;
    elevation?: 'default' | 'elevated';
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(({ className, interactive = false, elevation = 'default', ...props }, ref) => (
    <div
        ref={ref}
        className={cn(
            'rounded-xl border border-border bg-card text-card-foreground transition-[box-shadow,transform,border-color] duration-200 ease-emphasized',
            elevation === 'elevated' ? 'shadow-elevated hover:shadow-floating' : 'shadow-soft',
            interactive &&
                'cursor-pointer hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-elevated active:translate-y-0 active:shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background motion-reduce:transition-[box-shadow,border-color] motion-reduce:hover:translate-y-0',
            className,
        )}
        {...props}
    />
));
Card.displayName = 'Card';

/**
 * CardHeader holds the card's title block and, optionally, the controls that
 * act on the card.
 *
 * # Why `actions` exists
 *
 * It is the fix for a real defect. `pages/organizers/events/event/details.tsx`
 * renders `<Card className="relative">` with a `<div className="absolute
 * right-4 top-4">` holding Save and Delete, so both controls float on top of
 * the first thing inside the card — which is the "Cover image" section
 * heading. The buttons overlap live content, at every width, in both themes.
 *
 * That was invited from here. CardHeader was `flex flex-col space-y-1.5`: a
 * vertical stack and nothing else. A card whose header needs a title on the
 * left and a control on the right had NO affordance, so every page invented
 * one. Four did it four ways —
 * `flex flex-row items-center justify-between`,
 * `flex flex-row items-start justify-between gap-3 space-y-0`,
 * `flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between` —
 * and the one that could not get it to work took the controls out of flow
 * instead. A missing affordance does not stop anybody; it only decides how
 * badly the workaround goes.
 *
 * So the slot exists, and it lays out IN FLOW. Nothing here is absolutely
 * positioned, which is what makes overlap structurally unavailable rather
 * than merely discouraged: the actions occupy their own track, the title
 * column is `min-w-0` so a long title truncates instead of shoving the
 * buttons out of the card, and `flex-wrap` over a `basis-64` title column
 * drops the actions onto their own line on a narrow screen rather than
 * crushing them. On a 390px phone that is the difference between two
 * reachable buttons and two slivers.
 *
 * When `actions` is not passed this renders exactly what it always did — one
 * flex column — so none of the existing call sites moves.
 *
 * @param {object} props
 * @param {React.ReactNode} [props.actions] controls acting on this card
 */
export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
    actions?: React.ReactNode;
}

const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(({ className, actions, children, ...props }, ref) => {
    if (!actions) {
        return (
            <div ref={ref} className={cn('flex flex-col space-y-1.5 p-4 sm:p-6', className)} {...props}>
                {children}
            </div>
        );
    }
    return (
        <div
            ref={ref}
            className={cn('flex flex-wrap items-start justify-between gap-x-4 gap-y-3 p-4 sm:p-6', className)}
            {...props}
        >
            {/* basis-64 + grow: the title column claims the row when there is
                width for it and gives way to a new line when there is not.
                min-w-0 is what lets a long title's own truncation apply — a
                flex item defaults to `min-width: auto` and will refuse to
                shrink below its content, pushing the actions off the card
                instead of letting the text ellipsize. */}
            <div className="flex min-w-0 shrink grow basis-64 flex-col space-y-1.5">{children}</div>
            <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">{actions}</div>
        </div>
    );
});
CardHeader.displayName = 'CardHeader';

const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
    ({ className, ...props }, ref) => (
        <h3 ref={ref} className={cn('text-lg font-semibold leading-tight tracking-tight', className)} {...props} />
    ),
);
CardTitle.displayName = 'CardTitle';

const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
    ({ className, ...props }, ref) => (
        <p ref={ref} className={cn('text-sm text-muted-foreground', className)} {...props} />
    ),
);
CardDescription.displayName = 'CardDescription';

// Padding steps down below sm. 24px of gutter on each side of a 390px screen
// spends 12% of the viewport on nothing, and the tables and figures inside a
// card are exactly what needs that width back.
const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => <div ref={ref} className={cn('p-4 pt-0 sm:p-6 sm:pt-0', className)} {...props} />,
);
CardContent.displayName = 'CardContent';

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
    ({ className, ...props }, ref) => (
        <div ref={ref} className={cn('flex flex-wrap items-center gap-2 p-4 pt-0 sm:p-6 sm:pt-0', className)} {...props} />
    ),
);
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
