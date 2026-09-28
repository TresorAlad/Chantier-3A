import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { fetchSiteConfig, type SiteConfig } from '@/lib/site-config';

const defaultConfig: SiteConfig = {
    community_mode: false,
    host_scope: '',
    host_name: '',
    host_org: '',
    org_create_disabled: false,
    email_configured: false,
    contact_email: '',
    contact_form_enabled: false,
};

const SiteConfigContext = createContext<SiteConfig>(defaultConfig);

export function SiteConfigProvider({ children }: { children: ReactNode }) {
    const [config, setConfig] = useState<SiteConfig>(defaultConfig);

    useEffect(() => {
        fetchSiteConfig()
            .then(setConfig)
            .catch(() => setConfig(defaultConfig));
    }, []);

    return <SiteConfigContext.Provider value={config}>{children}</SiteConfigContext.Provider>;
}

export function useSiteConfig() {
    return useContext(SiteConfigContext);
}
