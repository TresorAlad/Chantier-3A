import type { ReactNode, HTMLAttributes } from 'react';
import { AlertTriangle, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface ErrorStateProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
    icon?: LucideIcon | undefined;
    title?: ReactNode;
    description?: ReactNode;
    onRetry?: (() => void) | undefined;
    retryLabel?: ReactNode;
}

/**
 * Shared error state — for failed fetches, failed mutations, etc. Distinct
 * from EmptyState: destructive-tinted, optional retry action.
 *
 *   <ErrorState
 *     description="Couldn't load your orders. Check your connection and try again."
 *     onRetry={() => refetch()}
 *   />
 */
const ErrorState = ({
    icon: Icon = AlertTriangle,
    title = 'Something went wrong',
    description,
    onRetry,
    retryLabel = 'Try again',
    className,
    ...props
}: ErrorStateProps) => (
    <div
        role="alert"
        className={cn(
            'flex animate-rise-in flex-col items-center justify-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 px-6 py-14 text-center',
            className,
        )}
        {...props}
    >
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10 text-destructive ring-1 ring-inset ring-destructive/20">
            <Icon className="h-6 w-6" aria-hidden="true" />
        </div>
        {title && <p className="text-base font-semibold text-foreground">{title}</p>}
        {description && <p className="max-w-sm text-balance text-sm text-muted-foreground">{description}</p>}
        {onRetry && (
            <Button variant="outline" size="sm" className="mt-1" onClick={onRetry}>
                {retryLabel}
            </Button>
        )}
    </div>
);

export { ErrorState };
