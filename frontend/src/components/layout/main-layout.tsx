import { useCallback, useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react';
import { Outlet } from 'react-router-dom';
import { useMediaQuery } from 'react-responsive';
import { MotionConfig } from 'framer-motion';
import { cn } from '@/lib/utils';
import SideNav from '../nav/side-nav';
import TopBar from '../nav/top-bar';
import PageTransition from '../motion/page-transition';

const TOP_BAR_HEIGHT = '4rem';
// Single source of truth for the expanded sidebar width. Both the desktop
// rail and the mobile drawer render at this width so the outer container
// and SideNav's own layout never disagree (a previous mismatch here — the
// wrapper fixed at w-16 while SideNav always rendered its w-60 expanded
// state on desktop — caused the main content pane to visually paint over
// and clip the nav labels down to their first couple of characters).
const SIDEBAR_WIDTH_CLASS = 'w-60';

const MainLayout = () => {
    const isMobile = useMediaQuery({ maxWidth: 640 });
    const [isExpanded, setIsExpanded] = useState(false);
    const sidenavRef = useRef<HTMLElement>(null);
    const toggleButtonRef = useRef<HTMLButtonElement>(null);

    const handleDrawerToggle = useCallback(
        (event: ReactMouseEvent) => {
            if (isMobile) {
                event.stopPropagation();
                setIsExpanded((prev) => !prev);
            }
        },
        [isMobile],
    );

    useEffect(() => {
        const handleClick = (event: MouseEvent) => {
            if (!isMobile) return;
            const target = event.target as Node | null;
            const clickedSidenav = sidenavRef.current?.contains(target);
            const clickedToggle = toggleButtonRef.current?.contains(target);
            if (!clickedSidenav && !clickedToggle) setIsExpanded(false);
        };
        document.addEventListener('click', handleClick);
        return () => document.removeEventListener('click', handleClick);
    }, [isMobile]);

    useEffect(() => {
        setIsExpanded(false);
    }, [isMobile]);

    return (
        <MotionConfig reducedMotion="user">
            <div className="flex h-screen flex-col bg-background text-foreground">
                {/* Measured at 390px: 36px tall. The skip link is the FIRST
                    thing a keyboard or switch user reaches on every console
                    page, and it is the one control on this shell that exists
                    only for people who need it — shipping it under target
                    size is the least defensible place in the app to do that.
                    `min-h-[44px]` with `inline-flex items-center` raises the
                    hit area without moving the label off its baseline, and
                    costs nothing at rest because the element is translated
                    out of view until focused. */}
                <a
                    href="#main-content"
                    className="fixed left-2 top-2 z-[100] inline-flex min-h-[44px] -translate-y-16 items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-elevated transition-transform focus:translate-y-0"
                >
                    Skip to content
                </a>
                <TopBar onMenuClick={handleDrawerToggle} toggleButtonRef={toggleButtonRef} />

                <div className="flex flex-1 overflow-hidden" style={{ marginTop: TOP_BAR_HEIGHT }}>
                    {!isMobile && (
                        <aside
                            className={cn(
                                'h-full shrink-0 overflow-y-auto overflow-x-hidden border-r border-sidebar-border shadow-elevated',
                                SIDEBAR_WIDTH_CLASS,
                            )}
                        >
                            <SideNav isExpanded={true} isMobile={false} />
                        </aside>
                    )}

                    <main
                        id="main-content"
                        tabIndex={-1}
                        className="relative flex-grow overflow-y-auto bg-muted/30 p-4 outline-none sm:p-6 lg:p-8"
                    >
                        <div className="mx-auto max-w-[1600px]">
                            <PageTransition>
                                <Outlet />
                            </PageTransition>
                        </div>
                        {isMobile && isExpanded && (
                            // The drawer scrim is the same token the two modal
                            // overlays use — one themed wash meaning "this
                            // layer is out of play", rather than three
                            // separate hardcoded blacks. See index.css.
                            <div className="fixed inset-0 z-10 animate-fade-in bg-scrim" onClick={() => setIsExpanded(false)} />
                        )}
                    </main>

                    {isMobile && (
                        <aside
                            ref={sidenavRef}
                            className={cn(
                                'fixed inset-y-0 left-0 z-20 h-full overflow-y-auto overflow-x-hidden shadow-floating transition-all duration-300 ease-emphasized',
                                isExpanded ? SIDEBAR_WIDTH_CLASS : 'w-0',
                            )}
                            style={{ top: TOP_BAR_HEIGHT }}
                        >
                            <SideNav isExpanded={isExpanded} isMobile={true} />
                        </aside>
                    )}
                </div>
            </div>
        </MotionConfig>
    );
};

export default MainLayout;
