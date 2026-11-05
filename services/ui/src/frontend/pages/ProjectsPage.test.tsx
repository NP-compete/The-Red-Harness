/**
 * Making and removing a project, now that the sidebar does neither.
 *
 * These cover what the three deleted `Sidebar — … project` describes
 * covered, because the capability moved rather than went away. The
 * `keepThreads` case is here deliberately: `deleteProjectThunk`
 * defaults it to **false**, which deletes every conversation in the
 * project, and this page's own label promises the opposite.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { renderWithProviders } from '../test-utils/render';
import ProjectsPage from './ProjectsPage';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}));

const createProject = vi.fn();
const deleteProject = vi.fn();
vi.mock('../services/projects-api', async () => {
  const actual =
    await vi.importActual<typeof import('../services/projects-api')>(
      '../services/projects-api'
    );
  return {
    ...actual,
    // The real thunks run; only the network is replaced. Mocking the
    // thunks instead hides the argument shape, which is the thing
    // most worth asserting here.
    getProjects: vi.fn(async () => []),
    createProject: (...args: unknown[]) => {
      createProject(...args);
      return Promise.resolve({ project_id: 'new', project_name: 'x' });
    },
    deleteProject: (...args: unknown[]) => {
      deleteProject(...args);
      return Promise.resolve({ deleted_thread_ids: [], missing: false });
    },
  };
});

const project = {
  project_id: 'p1',
  project_name: 'Migration',
  project_description: 'Billing move',
  thread_count: 3,
};

beforeEach(() => {
  createProject.mockReset();
  deleteProject.mockReset();
  mockNavigate.mockReset();
});

describe('ProjectsPage — removing a project', () => {
  it('takes two presses, so a stray click cannot do it', async () => {
    renderWithProviders(<ProjectsPage />, {
      preloadedState: { projects: { projects: [project], isLoadingProjects: false } },
    });

    await userEvent.click(screen.getByLabelText(/Delete Migration/i));
    expect(deleteProject).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole('button', { name: /Delete project/i }));
    await waitFor(() => expect(deleteProject).toHaveBeenCalled());
  });

  it('keeps the conversations, which is what the label promises', async () => {
    renderWithProviders(<ProjectsPage />, {
      preloadedState: { projects: { projects: [project], isLoadingProjects: false } },
    });

    await userEvent.click(screen.getByLabelText(/Delete Migration/i));
    await userEvent.click(screen.getByRole('button', { name: /Delete project/i }));

    // The thunk's default is false, and false deletes every thread
    // in the project. Asserting the exact value rather than that it
    // was called: the wrong default here is silent data loss.
    await waitFor(() =>
      expect(deleteProject).toHaveBeenCalledWith('p1', { keepThreads: true })
    );
  });

  it('can be backed out of', async () => {
    renderWithProviders(<ProjectsPage />, {
      preloadedState: { projects: { projects: [project], isLoadingProjects: false } },
    });

    await userEvent.click(screen.getByLabelText(/Delete Migration/i));
    await userEvent.click(screen.getByRole('button', { name: /^Cancel$/i }));
    expect(deleteProject).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/Delete Migration/i)).toBeInTheDocument();
  });
});
