import type { ElementType, HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import { formatMoney } from '@/lib/money';

interface MoneyProps extends HTMLAttributes<HTMLElement> {
    minor: number;
    currency: string | null | undefined;
    locale?: string | undefined;
    as?: ElementType | undefined;
}

// The one way money is rendered in this app.
//
// `lib/money.js` already owns the hard part — minor units, real ISO-4217
// exponents, the narrowSymbol trick that stops an en-US browser printing
// "ZAR 450.00" instead of "R 450.00". This component owns what that file
// cannot: how the result SITS on the page.
//
// # Why this exists rather than `{formatMoney(...)}` inline
//
// Tdev Festival prices events in whatever currency the organiser chose, and a payouts
// table can hold several at once. Those strings have wildly different widths —
// "¥4,500", "R 1,250.00", "35.939 KWD" — and proportional digits make even one
// currency jump: in Figtree a "1" is narrower than a "0", so a running total
// ticking 19 -> 20 visibly shifts every character to its left. Money that moves
// while you read it is money you re-read.
//
// Two fixes, and both have to be present:
//   1. `tnum` — tabular figures, so every digit takes the same advance width.
//      Figtree ships the feature but ALSO ships `pnum`, and proportional is
//      what you get by default, so it has to be asked for. See `.tnum` in
//      index.css.
//   2. Right alignment in columns — tabular figures fix digit width, not
//      symbol width, so "R " and "¥" still shift the start of the string. In a
//      column what must line up is the last digit, not the first character.
//
// `Money` itself carries `whitespace-nowrap`, because a currency string
// wrapping mid-amount is its own kind of wrong — no page should have to
// remember that. `<MoneyCell>` layers on the column-specific half:
// right alignment, so a table of mixed currencies keeps its last digits on
// one axis.

/**
 * Money renders an integer minor-unit amount in its own currency, with
 * tabular figures. Never wraps mid-amount.
 *
 * @param {object} props
 * @param {number} props.minor integer minor units (price_minor, total_minor…)
 * @param {string} props.currency ISO-4217 alpha-3
 * @param {string} [props.locale] override the browser's formatting locale
 * @param {string} [props.className]
 * @param {React.ElementType} [props.as] element to render, default `span`
 */
export function Money({ minor, currency, locale, className, as: Tag = 'span', ...rest }: MoneyProps) {
    const formatted = formatMoney(minor, currency, locale ? { locale } : undefined);
    return (
        <Tag className={cn('tnum whitespace-nowrap', className)} {...rest}>
            {formatted}
        </Tag>
    );
}

/**
 * MoneyCell is Money for a table column: right-aligned, so a column of mixed
 * currencies keeps its last digits on one axis and no row changes width when
 * a value does. Non-wrapping comes from `Money` itself.
 *
 * Renders a `<td>` by default; pass `as="div"` inside a non-table layout.
 */
export function MoneyCell({ minor, currency, locale, className, as: Tag = 'td', ...rest }: MoneyProps) {
    return (
        <Money
            as={Tag}
            minor={minor}
            currency={currency}
            locale={locale}
            className={cn('text-right', className)}
            {...rest}
        />
    );
}

/**
 * MoneyHeading is the large display treatment — a revenue figure at the top of
 * a stats page, an order total at checkout. Same tabular guarantee, sized for
 * a number that is the point of the screen rather than a cell in a table.
 */
export function MoneyHeading({ minor, currency, locale, className, ...rest }: Omit<MoneyProps, 'as'>) {
    return (
        <Money
            minor={minor}
            currency={currency}
            locale={locale}
            className={cn('font-display text-display-sm font-bold tracking-tight', className)}
            {...rest}
        />
    );
}

export default Money;
