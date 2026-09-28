import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { stackedCardItem, stackedCardsContainer } from '@/components/motion/motion-presets';

const DEFAULT_COLORS = [
    'bg-[hsl(var(--fest-violet))]',
    'bg-[hsl(var(--fest-blue))]',
    'bg-[hsl(var(--fest-orange))]',
    'bg-[hsl(var(--fest-cyan))]',
    'bg-[hsl(var(--fest-pink))]',
    'bg-[hsl(var(--fest-yellow))]',
    'bg-[hsl(var(--fest-green))]',
];

export interface StackedCardsProps {
    className?: string;
    count?: number;
    animate?: boolean;
}

/**
 * Motif charte : cartes empilées en éventail (coin de composition uniquement).
 */
export function StackedCards({ className, count = 6, animate = true }: StackedCardsProps) {
    const reduce = useReducedMotion();
    const n = Math.min(Math.max(count, 3), 8);
    const shouldAnimate = animate && !reduce;

    return (
        <motion.div
            className={cn('pointer-events-none relative h-48 w-48 sm:h-56 sm:w-56', className)}
            aria-hidden="true"
            initial={shouldAnimate ? 'hidden' : false}
            {...(shouldAnimate ? { animate: 'visible', variants: stackedCardsContainer } : {})}
        >
            {Array.from({ length: n }).map((_, i) => {
                const color = DEFAULT_COLORS[i % DEFAULT_COLORS.length];
                const rot = 5 + i * 2;
                return (
                    <motion.div
                        key={i}
                        className={cn(
                            'absolute left-1/2 top-1/2 aspect-square w-[72%] -translate-x-1/2 -translate-y-1/2 shadow-elevated',
                            'rounded-[2px]',
                            color,
                        )}
                        style={{
                            transform: `translate(calc(-50% + ${i * 10}px), calc(-50% - ${i * 10}px)) rotate(${rot}deg)`,
                            zIndex: i,
                            borderRadius: '3px 2px 4px 2px / 2px 3px 2px 4px',
                        }}
                        {...(shouldAnimate ? { variants: stackedCardItem } : {})}
                    />
                );
            })}
        </motion.div>
    );
}
