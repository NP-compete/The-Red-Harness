import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { FolderPlus, Trash2 } from 'lucide-react';

import { Button } from '@patternfly/react-core';
import { ProjectEditModal } from '../components/ProjectEditModal';
import { useAppDispatch, useAppSelector } from '../redux/hooks';
import {
  createProjectThunk,
  deleteProjectThunk,
  loadProjectsThunk,
  selectAllProjects,
  selectProjectsLoading,
} from '../redux/slices/projects';

/**
 * Every project, in one place.
 *
 * The sidebar already lists these, and this page is not a second
 * copy of that list: the sidebar shows projects *while you are in a
 * conversation*, nested under whatever you were reading, and it is
 * the wrong shape for "which of these should I open". Here they are
 * the whole screen, with the description somebody wrote and how much
 * is in each.
 *
 * **It reads the store the sidebar already fills.** Fetching again
 * would give this page its own answer, and two lists of projects
 * that can disagree is worse than one list in two places.
 *
 * **And it is now where projects are made and removed.** The
 * sidebar used to carry those controls under a PROJECTS heading
 * that said "No projects yet" to everyone who had none. Removing
 * that heading without moving the controls would have left the
 * product with no way to create a project at all — the page it
 * points at was read-only. They live here now, where the nav item
 * already promises they would be.
 */
export default function ProjectsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const projects = useAppSelector(selectAllProjects);
  const [creating, setCreating] = useState(false);
  // Which project the delete button is armed for. Two clicks, not
  // a confirm dialog: deleting a project does not delete its
  // conversations, so the cost of a slip is an undo rather than a
  // loss — but it should still take a deliberate second press.
  const [armed, setArmed] = useState<string | null>(null);
  const loading = useAppSelector(selectProjectsLoading);

  useEffect(() => {
    // Only when nothing is there yet: arriving here directly, rather
    // than through a conversation, is the case the sidebar has not
    // covered.
    if (projects.length === 0) void dispatch(loadProjectsThunk());
  }, [dispatch, projects.length]);

  return (
    <div className="h-full overflow-y-auto chat-scroll">
      <div className="mx-auto max-w-3xl px-6 py-8">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-medium">{t('projectsPage.title')}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {t('projectsPage.subtitle')}
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={() => setCreating(true)}>
            <FolderPlus className="w-4 h-4 mr-1.5" />
            {t('projectsPage.create')}
          </Button>
        </div>

        {!loading && projects.length === 0 && (
          <p className="mt-6 text-sm text-muted-foreground">{t('projectsPage.none')}</p>
        )}

        <ul className="mt-6 space-y-3 list-none">
          {projects.map((project) => (
            <li
              key={project.project_id}
              className="rounded border border-border bg-card hover:border-primary"
            >
              <div className="flex items-stretch">
                <button
                  type="button"
                  onClick={() => navigate(`/project/${project.project_id}`)}
                  className="flex-1 px-4 py-3 text-left"
                >
                  <p className="text-sm font-medium">{project.project_name}</p>
                  {project.project_description && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {project.project_description}
                    </p>
                  )}
                  <p className="mt-2 text-xs text-muted-foreground">
                    {t('projectsPage.threadCount', { count: project.thread_count })}
                  </p>
                </button>
                <div className="flex items-center pr-3">
                  {armed === project.project_id ? (
                    <div className="flex items-center gap-2">
                      {/* Said out loud, because the word "delete"
                          beside a project with conversations in it
                          reads as if the conversations go too. */}
                      <span className="text-xs text-muted-foreground">
                        {t('projectsPage.deleteKeepsThreads')}
                      </span>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => {
                          void dispatch(
                            deleteProjectThunk({
                              projectId: project.project_id,
                              // The thunk defaults to false,
                              // which deletes every conversation
                              // in the project. The label beside
                              // this button promises they are
                              // kept, so it must say so.
                              keepThreads: true,
                            })
                          );
                          setArmed(null);
                        }}
                      >
                        {t('projectsPage.confirmDelete')}
                      </Button>
                      <Button variant="plain" size="sm" onClick={() => setArmed(null)}>
                        {t('projectsPage.cancel')}
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="plain"
                      size="sm"
                      className="h-7 w-7 !p-0 text-muted-foreground hover:text-destructive"
                      aria-label={t('projectsPage.deleteProject', {
                        name: project.project_name,
                      })}
                      onClick={() => setArmed(project.project_id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <ProjectEditModal
        isOpen={creating}
        onClose={() => setCreating(false)}
        title={t('projectsPage.create')}
        onSave={async (name, description) => {
          try {
            const created = await dispatch(
              createProjectThunk({ name, description })
            ).unwrap();
            // Straight into it: somebody who just named a project
            // meant to put something in it.
            if (created?.project_id) navigate(`/project/${created.project_id}`);
            return true;
          } catch {
            return 'error';
          }
        }}
      />
    </div>
  );
}
