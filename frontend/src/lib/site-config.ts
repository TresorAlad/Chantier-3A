import { siteConfig as siteConfigApi } from '@/lib/api';

export interface SiteConfig {
    community_mode: boolean;
    host_scope: string;
    host_name: string;
    host_org: string;
    org_create_disabled: boolean;
    email_configured: boolean;
    contact_email?: string;
    contact_form_enabled?: boolean;
}

let cached: SiteConfig | null = null;

export async function fetchSiteConfig(): Promise<SiteConfig> {
    if (cached) {
        return cached;
    }
    const data = await siteConfigApi.get();
    cached = {
        community_mode: Boolean(data.community_mode),
        host_scope: data.host_scope ?? '',
        host_name: data.host_name ?? '',
        host_org: data.host_org ?? '',
        org_create_disabled: Boolean(data.org_create_disabled),
        email_configured: Boolean(data.email_configured),
        contact_email: data.contact_email?.trim() ?? '',
        contact_form_enabled: Boolean(data.contact_form_enabled),
    };
    return cached;
}

export function isStaffRole(role: string | undefined): boolean {
    return role === 'owner' || role === 'admin' || role === 'scanner';
}
