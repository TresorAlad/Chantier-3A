import { Home, CalendarDays, Settings, QrCode } from 'lucide-react';
import { NavItem } from './nav-item';
import { BrandLockup } from '@/components/brand/wordmark';
import { Separator } from '@/components/ui/separator';
import { useSiteConfig } from '@/context/use-site-config';

const defaultNavItems = [
    { to: '/admin', icon: Home, text: 'Home', end: true },
    { to: '/admin/events', icon: CalendarDays, text: 'Events' },
    { to: '/admin/scanner', icon: QrCode, text: 'Scanner' },
    { to: '/admin/settings', icon: Settings, text: 'Settings' },
];

const communityNavItems = [
    { to: '/admin', icon: Home, text: 'Tableau de bord', end: true },
    { to: '/admin/events', icon: CalendarDays, text: 'Événements' },
    { to: '/admin/scanner', icon: QrCode, text: 'Contrôle entrée' },
    { to: '/admin/settings', icon: Settings, text: 'Réglages' },
];

interface SideNavProps {
    isExpanded: boolean;
    isMobile: boolean;
}

const SideNav = ({ isExpanded, isMobile }: SideNavProps) => {
    const site = useSiteConfig();
    const navItems = site.community_mode ? communityNavItems : defaultNavItems;
    return (
        <div
            className={`flex h-full w-full flex-col overflow-hidden bg-sidebar transition-opacity duration-300 ${isMobile && !isExpanded ? 'invisible opacity-0' : 'visible opacity-100'}`}
        >
            <nav aria-label="Primary" className="flex-1 px-0 py-4">
                <ul className="space-y-1">
                    {navItems.map((item) => (
                        <NavItem key={item.to} {...item} isExpanded={isExpanded} />
                    ))}
                </ul>
            </nav>

            {/* The rail's foot. On mobile the drawer covers the top bar's
                wordmark, so this is where the mark lives while the drawer is
                open — and it is the same <BrandLockup> the top bar renders,
                not a second drawing of it.

                The seam above it is the ticket perforation: --notch is set to
                the sidebar's own ground so the two punched circles read as
                holes through the rail rather than as dots on it. */}
            <div className="shrink-0 px-4 pb-5 pt-1">
                <Separator variant="perforated" className="mb-4" decorative />
                <BrandLockup
                    size="xs"
                    tone="onDark"
                    className={`transition-opacity duration-200 ${isExpanded ? 'opacity-70' : 'opacity-0'}`}
                />
            </div>
        </div>
    );
};

export default SideNav;
