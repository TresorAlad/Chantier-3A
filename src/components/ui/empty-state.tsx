import type { ReactNode, HTMLAttributes } from 'react';
import type { LucideIcon } from 'lucide-react';

import { cn } from '@/lib/utils';

interface EmptyStateProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
    icon?: LucideIcon;
    title?: ReactNode;
    description?: ReactNode;
    action?: ReactNode;
}

/**
 * Shared "nothing here" state — for empty lists, empty search results, empty
 * dashboards, etc. Not an error: neutral tone, dashed border, muted icon.
 *
 *   <EmptyState
 *     icon={Ticket}
 *     title="No events yet"
 *     description="Create your first event to start selling tickets."
 *     action={<Button onClick={...}>Create event</Button>}
 *   />
 */
const EmptyState = ({ icon: Icon, title, description, action, className, ...props }: EmptyStateProps) => (
    <div
        role="status"
        className={cn(
            'flex animate-rise-in flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border bg-muted/30 px-6 py-14 text-center',
            className,
        )}
        {...props}
    >
        {Icon && (
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted text-muted-foreground ring-1 ring-inset ring-border">
                <Icon className="h-6 w-6" aria-hidden="true" />
            </div>
        )}
        {title && <p className="text-base font-semibold text-foreground">{title}</p>}
        {description && <p className="max-w-sm text-balance text-sm text-muted-foreground">{description}</p>}
        {action && <div className="mt-2">{action}</div>}
    </div>
);

export { EmptyState };
