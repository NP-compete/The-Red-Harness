import { beforeEach, describe, expect, it, vi } from 'vitest';

import { registerShellWorker } from '@/lib/register-sw';

function navigatorWith(register: unknown) {
  return { serviceWorker: { register } } as unknown as Navigator;
}

describe('registerShellWorker', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('registers the worker when the deployment wants one', async () => {
    const register = vi.fn().mockResolvedValue({ addEventListener: vi.fn() });
    await registerShellWorker({ enabled: true, nav: navigatorWith(register) });
    expect(register).toHaveBeenCalledWith('/sw.js', { scope: '/' });
  });

  it('registers none when the deployment turned the app off', async () => {
    const register = vi.fn();
    await registerShellWorker({ enabled: false, nav: navigatorWith(register) });
    expect(register).not.toHaveBeenCalled();
  });

  it('does nothing where the browser has no worker support', async () => {
    const nav = {} as Navigator;
    await expect(registerShellWorker({ enabled: true, nav })).resolves.toBeNull();
  });

  it('does not take the page down when registration fails', async () => {
    // A worker is an enhancement. The application works without one,
    // and an exception here would stop it loading at all.
    const register = vi.fn().mockRejectedValue(new Error('refused'));
    await expect(
      registerShellWorker({ enabled: true, nav: navigatorWith(register) }),
    ).resolves.toBeNull();
  });

  it('reports the registration so the page can watch for an update', async () => {
    const registration = { addEventListener: vi.fn() };
    const register = vi.fn().mockResolvedValue(registration);
    const found = await registerShellWorker({ enabled: true, nav: navigatorWith(register) });
    expect(found).toBe(registration);
  });
});
