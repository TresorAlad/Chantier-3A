import type { MouseEvent, RefObject } from 'react';
import { Link } from 'react-router-dom';
import { Menu, User, ChevronDown, Building2, LogOut, Moon, Sun, Check } from 'lucide-react';
import { useAuth } from '@/context/use-auth';
import { useTheme } from '@/components/theme-provider';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { TdevLogo } from '@/components/brand/tdev-logo';

interface TopBarProps {
    onMenuClick: (event: MouseEvent<HTMLButtonElement>) => void;
    toggleButtonRef: RefObject<HTMLButtonElement>;
}

const TopBar = ({ onMenuClick, toggleButtonRef }: TopBarProps) => {
    const { user, signOut, orgs, activeOrg, switchOrg } = useAuth();
    const { theme, setTheme } = useTheme();

    return (
        <nav className="fixed left-0 right-0 top-0 z-50 flex h-16 items-center justify-between border-b border-sidebar-border bg-sidebar px-4 text-sidebar-foreground shadow-elevated sm:px-6">
            {/* min-w-0 so this group is the one that yields if anything ever
                has to. The right-hand group is where a user signs out and
                switches org; it must never be the side that gets squeezed. */}
            <div className="flex min-w-0 items-center gap-3">
                {/* This is the ONLY route to the side nav on a phone, on all
                    14 console pages, and gate staff work the door on a phone.
                    It measured 22×22 — under WCAG 2.2 AA's 24×24 floor and
                    less than a quarter of the 44×44 target the platform HIGs
                    ask for. The hit area is now 44×44 while the glyph stays
                    at 22, so nothing about the chrome looks heavier; the
                    negative margin keeps the icon optically flush with the
                    wordmark rather than pushed in by its own padding. */}
                <button
                    ref={toggleButtonRef}
                    className="-ml-2.5 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar-background sm:hidden"
                    onClick={onMenuClick}
                    aria-label="Open navigation menu"
                >
                    <Menu size={22} aria-hidden="true" />
                </button>
                {/* The console chrome is a fixed ink shell in both themes, so
                    the wordmark is pinned to its on-dark tone rather than
                    following the page. Below sm only the tile draws — at
                    390px the org switcher and the account menu need the
                    width more than the word does. */}
                <Link
                    to="/"
                    aria-label="Tdev Festival home"
                    // Measured at 390px: 46x39 — the lockup's own height,
                    // because the anchor was a bare inline box wrapping it.
                    // `inline-flex min-h-[44px] items-center` gives the link
                    // a real target without resizing the mark: the tile and
                    // wordmark keep their `size` step and simply centre in a
                    // taller box, which the 64px bar already had room for.
                    className="inline-flex min-h-[44px] items-center rounded-md transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar-background"
                >
                    <TdevLogo size="md" />
                </Link>
            </div>

            {/* shrink-0: this group holds the only route to signing out and
                to switching org, and it is not allowed to be the thing that
                gets pushed out of the viewport. It was — see below. */}
            <div className="flex shrink-0 items-center gap-2">
                {/* MEASURED DEFECT, both themes, 390px: with a long org name
                    this trigger was 220px wide, which put the account menu's
                    right edge at 420px against a 390px viewport — the button
                    was entirely off-canvas and unreachable. On a phone with
                    more than one org a user could not sign out or switch org
                    at all.

                    It survived every sweep this session because the demo box
                    seeds exactly ONE organisation and this whole block only
                    renders when there is more than one, so the measurement
                    pass was structurally blind to it. Reproduced by rewriting
                    the `/api/auth/me` envelope to carry two orgs, one with a
                    deliberately long name; `body{overflow-x:hidden}` means
                    the page never scrolls sideways to reveal it, so only
                    per-element rects show it at all.

                    Below sm the trigger collapses to the icon alone — 220px
                    down to 44px — which is the same trade the wordmark
                    already makes here (`hideWordBelowSm`). The name has not
                    vanished: it is the button's accessible name, and the menu
                    it opens now marks the active org with a check, which it
                    did not before and which the icon-only state makes
                    necessary rather than merely nice. From sm up the label
                    returns, still truncated. */}
                {orgs?.length > 1 && (
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button
                                variant="ghost"
                                size="icon"
                                aria-label={`Switch organisation — currently ${activeOrg?.name || 'none selected'}`}
                                className="shrink-0 gap-2 text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground sm:w-auto sm:px-4"
                            >
                                <Building2 size={18} />
                                <span className="hidden max-w-[140px] truncate sm:inline">{activeOrg?.name || 'Select org'}</span>
                                <ChevronDown size={14} className="hidden sm:block" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="max-w-[calc(100vw-2rem)]">
                            <DropdownMenuLabel>Organizations</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            {orgs.map((org) => (
                                <DropdownMenuItem key={org.id} onClick={() => switchOrg(org.id)}>
                                    {org.id === activeOrg?.id ? (
                                        <Check className="mr-2 h-4 w-4 shrink-0 text-primary-emphasis" aria-hidden="true" />
                                    ) : (
                                        <Building2 className="mr-2 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                                    )}
                                    <span className="truncate">{org.name}</span>
                                    {org.id === activeOrg?.id && <span className="sr-only"> (current)</span>}
                                </DropdownMenuItem>
                            ))}
                        </DropdownMenuContent>
                    </DropdownMenu>
                )}

                {/* `-mx-1` gives back the 4px each side that Button's `icon`
                    size (44×44 below `sm`, 36×36 from `sm` up) would
                    otherwise add to the row, so the icons stay where they
                    were relative to each other and to the account menu's
                    edge instead of pushing outward. */}
                <Button
                    variant="ghost"
                    size="icon"
                    className="-mx-1 shrink-0 text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                    aria-label="Toggle theme"
                >
                    {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
                </Button>

                {user && (
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="-mx-1 shrink-0 text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                                aria-label="Account menu"
                            >
                                <User size={20} />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuLabel className="truncate">{user.email}</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem asChild>
                                <Link to="/">Visitor site</Link>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={signOut} className="text-destructive focus:text-destructive">
                                <LogOut className="mr-2 h-4 w-4" />
                                Sign out
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                )}
            </div>
        </nav>
    );
};

export default TopBar;
