import type { LucideIcon } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface NavItemProps {
    to: string;
    icon: LucideIcon;
    text: string;
    isExpanded: boolean;
    end?: boolean;
}

export const NavItem = ({ to, icon: Icon, text, isExpanded, end = false }: NavItemProps) => {
    return (
        <li className="list-none px-2">
            <NavLink
                to={to}
                end={end}
                // Measured at 390px with the drawer open: 224×40 — the row
                // spans the sidebar's width fine, but at 40 the height was
                // 4px short of the 44px target gate staff need on a phone.
                // `py-2.5` (10px top+bottom, 20+20=40 total with the 20px
                // icon) becomes `py-3` (12px, 24+20=44) — the icon keeps its
                // own `h-5 w-5` size, so only the row's own height grows, not
                // the glyph inside it. No negative margin is needed here: a
                // full-width row growing taller doesn't push anything
                // sideways, it just gives four rows 16px more total height
                // between them, which is the point.
                className={({ isActive }) =>
                    cn(
                        'relative flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar-background',
                        isActive
                            ? 'text-sidebar-primary-foreground'
                            : 'text-sidebar-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                    )
                }
            >
                {({ isActive }) => (
                    <>
                        {/* Shared layoutId so the highlight slides between items on
                            navigation instead of just popping in/out — the one bit
                            of signature motion in the console chrome. MainLayout
                            wraps this tree in <MotionConfig reducedMotion="user">,
                            so this is automatically inert for prefers-reduced-motion. */}
                        {isActive && (
                            <motion.span
                                layoutId="active-nav-pill"
                                className="absolute inset-0 rounded-lg bg-sidebar-primary"
                                transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                            />
                        )}
                        <Icon className="relative z-10 h-5 w-5 shrink-0" aria-hidden="true" />
                        <span className={cn('relative z-10 truncate transition-opacity', isExpanded ? 'opacity-100' : 'opacity-0')}>
                            {text}
                        </span>
                    </>
                )}
            </NavLink>
        </li>
    );
};

export default NavItem;
