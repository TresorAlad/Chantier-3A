import * as React from 'react';

import { cn } from '@/lib/utils';

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
    ({ className, type, ...props }, ref) => {
    return (
        <input
            type={type}
            className={cn(
                // h-11 (44px) below sm, h-9 (36px) from sm up. It was h-10 —
                // 40px — which is comfortable but is still under the 44px
                // target this app holds itself to at 390px, and a field is
                // the most-tapped control in the product after a button.
                // It is also what makes `form.tsx`'s FormLabel entitled to
                // WCAG 2.5.5's "Equivalent" exception: the label stays
                // compact because the field it labels is a real 44px target,
                // and that only holds while this number does.
                // `text-base` below sm stops iOS Safari zooming the whole
                // page on focus (it does that under 16px).
                'flex h-11 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-soft transition-[color,border-color,box-shadow] duration-150 file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground hover:border-ring/60 focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-destructive aria-[invalid=true]:focus-visible:ring-destructive sm:h-9 sm:text-sm',
                className,
            )}
            ref={ref}
            {...props}
        />
    );
    },
);
Input.displayName = 'Input';

export { Input };
