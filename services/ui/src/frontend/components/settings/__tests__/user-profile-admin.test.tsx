import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { UserProfileAdmin } from '../UserProfileAdmin';
import * as api from '../../../services/user-admin-api';

/**
 * E9-T3. What the screen shows, and the one distinction it must not
 * blur: "the policy refused you" and "this deployment cannot make
 * that change at all" look the same if you only grey the control
 * out, and the first sends somebody looking for an administrator
 * while the second has no administrator to find.
 */

const PERMS = (profile: Partial<api.ClassPermission>): api.UserPermissions => ({
  user_id: 'bob',
  actor_role: 'admins',
  target_role: 'users',
  classes: [
    { field_class: 'profile', allowed: true, reasons: [], writable_here: true, ...profile },
    {
      field_class: 'membership',
      allowed: true,
      reasons: [],
      writable_here: false,
    },
    {
      field_class: 'entitlement',
      allowed: false,
      reasons: ["role 'admins' may not change 'entitlement' fields on role 'users'"],
      writable_here: false,
    },
  ],
});

function stub(perms: api.UserPermissions) {
  vi.spyOn(api, 'readPermissions').mockResolvedValue(perms);
  vi.spyOn(api, 'readProfile').mockResolvedValue({
    user_id: 'bob',
    fields: { display_name: 'Bob' },
    writable_fields: ['display_name', 'title'],
  });
}

async function lookUp() {
  await userEvent.type(screen.getByLabelText(/username/i), 'bob');
  await userEvent.click(screen.getByRole('button', { name: /look up/i }));
}

describe('UserProfileAdmin', () => {
  it('offers the fields when the policy allows it', async () => {
    stub(PERMS({}));
    render(<UserProfileAdmin />);
    await lookUp();
    expect(await screen.findByDisplayValue('Bob')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save profile/i })).toBeInTheDocument();
  });

  it('shows the policy’s own reason when it refuses', async () => {
    stub(
      PERMS({
        allowed: false,
        reasons: ["role 'admins' may not change 'profile' fields on role 'owners'"],
      }),
    );
    render(<UserProfileAdmin />);
    await lookUp();
    // Twice, deliberately: once in the per-class list and once
    // where the editor would have been. Both are the policy's own
    // sentence rather than a generic "not permitted".
    await waitFor(() =>
      expect(screen.getAllByText(/may not change 'profile' fields/).length).toBe(2),
    );
    expect(screen.queryByRole('button', { name: /save profile/i })).toBeNull();
  });

  it('says a class lives in the identity provider rather than that it was refused', async () => {
    stub(PERMS({}));
    render(<UserProfileAdmin />);
    await lookUp();
    // membership is `allowed: true` but not writable here, so the
    // reason shown must be about where it lives, not about a role.
    // Two of the three classes are in that position.
    await waitFor(() =>
      expect(screen.getAllByText(/identity provider, not here/).length).toBe(2),
    );
    // And the entitlement refusal must not be dressed up as one of
    // them: a policy refusal says why, in the policy's words.
    expect(screen.queryByText(/may not change 'entitlement'/)).toBeNull();
  });

  it('clears the previous person when the box changes', async () => {
    stub(PERMS({}));
    render(<UserProfileAdmin />);
    await lookUp();
    expect(await screen.findByDisplayValue('Bob')).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/username/i), 'x');
    // Leaving one person's answers on screen beside another name is
    // the kind of thing somebody acts on.
    await waitFor(() => expect(screen.queryByDisplayValue('Bob')).toBeNull());
  });

  it('shows the agent’s refusal verbatim when the write is rejected', async () => {
    stub(PERMS({}));
    vi.spyOn(api, 'saveProfile').mockResolvedValue({
      ok: false,
      detail: 'the policy engine could not be reached, so the change was refused',
    });
    render(<UserProfileAdmin />);
    await lookUp();
    await userEvent.click(await screen.findByRole('button', { name: /save profile/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be reached/);
  });
});
