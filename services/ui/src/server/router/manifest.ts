import { getSettings } from "../utils/settings.js";

export interface ManifestIcon {
  src: string;
  sizes: string;
  type?: string;
  purpose?: string;
}

export interface WebManifest {
  name: string;
  short_name: string;
  start_url: string;
  scope: string;
  display: string;
  orientation: string;
  theme_color: string;
  background_color: string;
  icons: ManifestIcon[];
}

/**
 * How the installed application describes itself.
 *
 * Generated from the branding the masthead already reads, rather
 * than committed as a file. A static manifest is a second place the
 * product name lives, and the two disagree the first time somebody
 * renames a deployment: the window title changes and the dock icon
 * keeps the old one until the next image build.
 */
export function buildManifest(
  over?: Partial<Pick<WebManifest, "short_name" | "display" | "orientation">>,
): WebManifest {
  const { branding, pwa } = getSettings();
  const short = over?.short_name || pwa.manifest.short_name || branding.title;

  return {
    name: branding.title,
    short_name: short,
    start_url: "/",
    scope: "/",
    display: over?.display || pwa.manifest.display,
    orientation: over?.orientation || pwa.manifest.orientation,
    // The light theme's colours: the manifest describes the window
    // chrome before any stylesheet has loaded, and a dark splash on
    // a light app is worse than the reverse.
    theme_color: branding.colors.light.primary,
    background_color: branding.colors.light.background,
    icons: iconsFrom(branding.logo_url, branding.logo_maskable_url),
  };
}

/**
 * The icon set, from the logo a deployment configures.
 *
 * Declared at the sizes a browser looks for rather than one
 * entry: below 192 the install prompt substitutes a generic icon.
 *
 * Nothing is declared maskable unless the deployment supplies an
 * image drawn for it. A platform crops a maskable icon to roughly
 * its middle four fifths, which looks native for a logo drawn
 * with that in mind and removes the first and last letters of a
 * wordmark. Every deployment sets its own logo and the product
 * cannot see it, so it cannot tell which it has. Declaring them
 * all maskable traded a cosmetic problem for a destructive one —
 * a letterboxed icon is slightly ugly, a cropped wordmark is the
 * product name with the ends missing, and nobody seeing it knows
 * which setting did that.
 */
function iconsFrom(
  logo: string | undefined,
  maskable: string | undefined,
): ManifestIcon[] {
  const icons: ManifestIcon[] = [];

  // The logo is optional, and a deployment that has not set one
  // is ordinary rather than broken. An icon list pointing at
  // nothing is worse than none: the browser fetches each entry,
  // fails, and falls back to a generic icon anyway.
  if (logo) {
    const type = typeOf(logo);
    icons.push({ src: logo, sizes: "192x192", type, purpose: "any" });
    icons.push({ src: logo, sizes: "512x512", type, purpose: "any" });
  }

  if (maskable) {
    icons.push({
      src: maskable,
      sizes: "512x512",
      type: typeOf(maskable),
      purpose: "maskable",
    });
  }

  return icons;
}

function typeOf(file: string): string {
  if (file.endsWith(".svg")) return "image/svg+xml";
  if (file.endsWith(".png")) return "image/png";
  return "image/jpeg";
}
