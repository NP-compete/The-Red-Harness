export interface BrandingThemeColors {
  primary: string;
  accent: string;
  background: string;
  foreground: string;
}

export interface BrandingConfig {
  logo_url: string;
  title: string;
  version: string;
  favicon_url?: string;
  colors: {
    light: BrandingThemeColors;
    dark: BrandingThemeColors;
  };
}

export interface FeaturesConfig {
  debug_mode_default: boolean;
  auth_enabled: boolean;
  mcp_apps_enabled?: boolean;
  mcp_dcr_enabled?: boolean;
  memory_enabled: boolean;
  /**
   * Whether Skills is visible to everyone. Optional, and absent
   * means visible — an older config without the key must not
   * silently hide a tab that used to be there.
   */
  skills_visible_to_all?: boolean;
  subagents_visible_to_all?: boolean;
  prompt_visible_to_all?: boolean;
}

export interface ContentConfig {
  greeting: string;
  greeting_anonymous: string;
  subtitle: string;
  quick_prompts_heading: string;
  quick_prompts: string[];
  input_placeholder: string;
  welcome_heading: string;
  welcome_subtitle: string;
}

function getConfigApiBase(): string {
  const basePath = (window.APP_DATA?.basePath || '').replace(/\/$/, '');
  return `${basePath}/api/config`;
}

export const fetchBranding = async (): Promise<BrandingConfig> => {
  const res = await fetch(`${getConfigApiBase()}/branding`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error("Failed to load branding config");
  }
  return res.json();
};

export const fetchFeatures = async (): Promise<FeaturesConfig> => {
  const res = await fetch(`${getConfigApiBase()}/features`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error("Failed to load features config");
  }
  return res.json();
};

export const fetchContent = async (): Promise<ContentConfig> => {
  const res = await fetch(`${getConfigApiBase()}/content`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error("Failed to load content config");
  }
  return res.json();
};

export interface PwaConfig {
  enabled: boolean;
  install_prompt: boolean;
  manifest: { short_name: string; display: string; orientation: string };
  notifications: {
    enabled: boolean;
    platforms: string[];
    events: Record<string, boolean>;
    include_detail: boolean;
    badge: boolean;
  };
  push: { enabled: boolean; vapid_public_key: string };
}

/**
 * What the deployment says about notifications.
 *
 * A failure is reported as nothing rather than as defaults: guessing
 * that notifications are on would prompt for permission somewhere a
 * deployment had decided against it.
 */
export async function getPwaConfig(): Promise<PwaConfig | null> {
  try {
    const response = await fetch('/api/config/pwa');
    if (!response.ok) return null;
    return (await response.json()) as PwaConfig;
  } catch {
    return null;
  }
}
