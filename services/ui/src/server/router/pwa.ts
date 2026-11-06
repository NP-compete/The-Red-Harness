import { getSettings } from "../utils/settings.js";

/**
 * What the browser is allowed to know about notifications.
 *
 * The platform allowlist travels to the client because the client is
 * where the permission prompt happens, and a prompt on a platform
 * where delivery does not work is the one thing worth avoiding.
 *
 * Only the public half of a push key, and no field for the private
 * one — a private key reaching the browser is the entire failure, so
 * there is nowhere for it to go rather than a check that it did not.
 */
export function buildPwaResponse() {
  const { pwa } = getSettings();
  return {
    // A cached answer outlives the deployment decision that made it.
    cacheControl: "no-store",
    body: {
      enabled: pwa.enabled,
      install_prompt: pwa.install_prompt,
      manifest: pwa.manifest,
      notifications: pwa.notifications,
      push: {
        enabled: pwa.push.enabled,
        vapid_public_key: pwa.push.vapid_public_key,
      },
    },
  };
}
