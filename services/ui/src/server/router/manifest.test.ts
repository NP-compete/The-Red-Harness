import { describe, it, expect } from "vitest";

import { buildManifest } from "./manifest.js";
import { getSettings } from "../utils/settings.js";

/**
 * The installed app, described from the one place the name lives.
 *
 * A static manifest would be a second place to change the product
 * name, and the two would disagree the first time somebody renamed
 * the deployment and the dock icon kept the old one.
 */
describe("buildManifest", () => {
  const branding = () => getSettings().branding;

  it("takes its name from the branding the masthead reads", () => {
    expect(buildManifest().name).toBe(branding().title);
  });

  it("falls back to the same name when no short one is configured", () => {
    expect(buildManifest().short_name).toBe(branding().title);
  });

  it("uses a configured short name when there is one", () => {
    const made = buildManifest({ short_name: "Pilot" });
    expect(made.short_name).toBe("Pilot");
  });

  it("takes its colours from branding, not from a copy", () => {
    expect(made().theme_color).toBe(branding().colors.light.primary);
    expect(made().background_color).toBe(branding().colors.light.background);
  });

  it("opens in its own window rather than a browser tab", () => {
    // The point of installing it.
    expect(made().display).toBe("standalone");
  });

  it("starts at the application, not at whatever was last open", () => {
    expect(made().start_url).toBe("/");
  });

  it("is scoped to the application", () => {
    expect(made().scope).toBe("/");
  });

  describe("a deployment with no logo", () => {
    /**
     * The logo is optional — the settings schema says so, and a
     * deployment that has not set one is a normal deployment, not
     * a broken one.
     *
     * An icon list pointing at nothing is worse than no icon
     * list: the browser fetches the entries, fails, and falls
     * back to a generic icon anyway, having shown a broken one
     * first.
     */
    const noLogo = () => {
      const settings = getSettings();
      const held = settings.branding.logo_url;
      // Restored by the caller, so one case cannot disturb the next.
      return {
        apply: () => {
          (settings.branding as { logo_url?: string }).logo_url = undefined;
        },
        restore: () => {
          (settings.branding as { logo_url?: string }).logo_url = held;
        },
      };
    };

    it("still builds a manifest", () => {
      const swap = noLogo();
      swap.apply();
      try {
        expect(buildManifest().name).toBe(branding().title);
      } finally {
        swap.restore();
      }
    });

    it("offers no icons rather than icons pointing nowhere", () => {
      const swap = noLogo();
      swap.apply();
      try {
        expect(buildManifest().icons).toEqual([]);
      } finally {
        swap.restore();
      }
    });
  });

  describe("icons", () => {
    // A logo, set explicitly. The shipped default is the empty
    // string — `noLogo` above covers that case on purpose — so a
    // test that reads ambient settings asserts nothing about the
    // icon logic and fails wherever no deployment config is loaded.
    const withLogo = (url = "/assets/logo.svg") => {
      const settings = getSettings();
      const held = settings.branding.logo_url;
      return {
        apply: () => {
          (settings.branding as { logo_url?: string }).logo_url = url;
        },
        restore: () => {
          (settings.branding as { logo_url?: string }).logo_url = held;
        },
      };
    };

    const withLogoMade = (fn: (m: ReturnType<typeof buildManifest>) => void) => {
      const swap = withLogo();
      swap.apply();
      try {
        fn(buildManifest());
      } finally {
        swap.restore();
      }
    };

    it("declares at least one", () => {
      withLogoMade((m) => expect(m.icons.length).toBeGreaterThan(0));
    });

    it("declares one large enough for an install prompt", () => {
      // Below 192 the browser substitutes a generic icon.
      withLogoMade((m) => {
        const big = m.icons.filter((i) => i.sizes.split("x").every((n) => Number(n) >= 192));
        expect(big.length).toBeGreaterThan(0);
      });
    });

    it("declares none maskable unless the deployment supplied one", () => {
      // This asserted the opposite. Declaring the configured
      // logo maskable avoided letterboxing, and bought that by
      // letting the platform crop every deployment's logo to
      // its middle four fifths — which takes the ends off a
      // wordmark. The product cannot see the image, so it
      // cannot know which it has, and the default is now the
      // one that cannot destroy anything. A deployment with a
      // logo drawn for cropping sets `logo_maskable_url`.
      expect(made().icons.some((i) => i.purpose?.includes("maskable"))).toBe(false);
    });

    it("points them at the configured logo rather than a hard-coded path", () => {
      withLogoMade((m) => expect(m.icons[0].src).toBe(branding().logo_url));
    });
  });

  function made(over?: Parameters<typeof buildManifest>[0]) {
    return buildManifest(over);
  }
});
