import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  type MenuToggleElement,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
  SearchInput,
  Tooltip,
} from '@patternfly/react-core';
import {
  MessageSquare,
  Trash2,
  Edit3,
  Plus,
  Settings,
  LogOut,
  Folder,
  FolderPlus,
  FolderMinus,
  Clock,
  Sliders,
  Pin,
  PinOff,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { logout } from '../services/logout';
import { useSelector } from 'react-redux';
import type { StreamingState } from '../redux/slices/chats';
import { ChatStatusDot } from './ChatStatusDot';
import { ChatRowTitle } from './ChatRowTitle';
import { ThreadSelectionBar } from './ThreadSelectionBar';
import { TagFilter } from './TagFilter';
import { useThreadSelection } from '../hooks/useThreadSelection';
import { idsToDelete } from '../lib/bulk-delete';
import { listAllThreadIds } from '../services/agent-rest';
import {
  activityByChat,
  type ChatActivity,
  type ChatForActivity,
} from '../lib/chat-activity';
import { cn } from '@/lib/utils';
import type { SidebarChatItem, SidebarProject } from '../types/chat';
import { SearchResults } from './SearchResults';
import { emptyListReason } from '../lib/empty-list-reason';
import { useThreadSearch } from '../hooks/useThreadSearch';
import { useAgentHealth } from '../hooks/useAgentHealth';
import { useSidebarDragDrop } from '../hooks/useSidebarDragDrop';
import { ProjectEditModal } from './ProjectEditModal';

interface SidebarProps {
  userName?: string;
  currentChatId?: string;
  chatHistory: SidebarChatItem[];
  tokenExpiry?: Date;
  onNewChat: (projectId?: string) => void;
  onSelectChat: (chatId: string) => void;
  onDeleteChat: (chatId: string) => void;
  /** Delete several at once; absent means the sidebar deletes one by one. */
  onDeleteMany?: (ids: string[]) => void | Promise<void>;
  onRenameChat: (chatId: string, newTitle: string) => void;
  /** Pin or unpin, written through to the agent so it follows the person. */
  onTogglePin?: (chatId: string, pinned: boolean) => void;
  projects?: SidebarProject[];
  onCreateProject?: (name: string, description?: string) => Promise<string | null>;
  onUpdateProject?: (projectId: string, name?: string, description?: string) => Promise<boolean>;
  onDeleteProject?: (
    projectId: string,
    options?: { keepThreads?: boolean },
  ) => Promise<boolean>;
  onAssignThread?: (threadId: string, projectId: string | null) => Promise<boolean>;
  onUnassignAll?: (projectId: string) => Promise<boolean>;
}

function SidebarComponent({
  userName = 'User',
  currentChatId,
  chatHistory,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  tokenExpiry,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  onDeleteMany,
  onRenameChat,
  onTogglePin,
  projects = [],
  onCreateProject,
  onUpdateProject,
  onDeleteProject,
  onAssignThread,
  onUnassignAll,
}: SidebarProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const agentHealth = useAgentHealth();
  const streamingStates = useSelector(
    (state: { chats: { streamingStates: Record<string, StreamingState> } }) =>
      state.chats.streamingStates,
  );
  // The loaded chats, not `chatHistory`: the sidebar's own items carry
  // no messages, and the last message is what says whether a finished
  // turn answered or stopped to ask for an integration.
  const loadedChats = useSelector(
    (state: { chats: { chats: ChatForActivity[] } }) => state.chats.chats,
  );
  const activity = useMemo(
    () => activityByChat(streamingStates, loadedChats),
    [streamingStates, loadedChats],
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [editingChat, setEditingChat] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [deletingChatId, setDeletingChatId] = useState<string | null>(null);
  const [deletingProjectId, setDeletingProjectId] = useState<string | null>(null);
  const [unassigningProjectId, setUnassigningProjectId] = useState<string | null>(null);
  const [unassignBusy, setUnassignBusy] = useState(false);
  const [projectDeleteBusy, setProjectDeleteBusy] = useState(false);
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<SidebarProject | null>(null);
  const [assignMenuChatId, setAssignMenuChatId] = useState<string | null>(null);

  const assignHandler = onAssignThread ?? (async () => false);
  const drag = useSidebarDragDrop(assignHandler);

  // Two searches, deliberately. The local filter is instant and covers
  // titles of threads already loaded; the server one covers message
  // bodies, including threads this browser has never seen.
  const [taggedIds, setTaggedIds] = useState<string[] | null>(null);
  const [selecting, setSelecting] = useState(false);
  const selection = useThreadSelection(
    useMemo(() => chatHistory.map((chat) => chat.id), [chatHistory]),
    chatHistory.length,
  );

  const filteredChats = useMemo(() => {
    // A tag filter narrows the list the same way the search box does,
    // and the two compose.
    const byTag =
      taggedIds === null
        ? chatHistory
        : chatHistory.filter((chat) => taggedIds.includes(chat.id));
    const q = searchQuery.trim().toLowerCase();
    if (!q) return byTag;
    return byTag.filter(
      (chat) =>
        chat.title.toLowerCase().includes(q) || chat.preview.toLowerCase().includes(q)
    );
  }, [chatHistory, searchQuery, taggedIds]);

  const contentSearch = useThreadSearch(searchQuery);
  const locallyMatched = useMemo(
    () => new Set(filteredChats.map((chat) => chat.id)),
    [filteredChats],
  );

  const knownProjectIds = useMemo(
    () => new Set(projects.map((p) => p.id)),
    [projects],
  );

  const unassignedChats = useMemo(
    () =>
      filteredChats.filter(
        (c) => !c.project_id || !knownProjectIds.has(c.project_id),
      ),
    [filteredChats, knownProjectIds],
  );

  // Grouped by what each conversation needs from the reader.
  //
  // Flat and ordered by time, a chat waiting on an approval sat
  // wherever it happened to fall, and the only way to find it was to
  // remember it existed. Order is deliberate: blocked on you, then
  // working, then everything else.
  const unassignedSections = useMemo(() => {
    const buckets: Record<ChatActivity, SidebarChatItem[]> = {
      'needs-input': [],
      running: [],
      failed: [],
      idle: [],
    };
    // Pinned is a section, not a badge, and a pinned conversation
    // appears in it *instead of* its run-state section rather than in
    // both: the same row twice in one list is the reader wondering
    // which of the two is the real one.
    const pinned: SidebarChatItem[] = [];
    for (const chat of unassignedChats) {
      if (chat.pinned) pinned.push(chat);
      else buckets[activity[chat.id] ?? 'idle'].push(chat);
    }
    return (
      [
        // First, and above run state: somebody pinned this because
        // they want it where they can find it, which outranks what
        // the agent happens to be doing in it.
        { key: 'pinned', labelKey: 'sidebar.sectionPinned', chats: pinned },
        { key: 'needs-input', labelKey: 'sidebar.sectionNeedsInput', chats: buckets['needs-input'] },
        { key: 'running', labelKey: 'sidebar.sectionInProgress', chats: buckets.running },
        // Above completed: a run that died is work that did not
        // happen, and filing it with the answered ones loses it.
        { key: 'failed', labelKey: 'sidebar.sectionStopped', chats: buckets.failed },
        { key: 'idle', labelKey: 'sidebar.sectionCompleted', chats: buckets.idle },
      ] as const
    ).filter((section) => section.chats.length > 0);
  }, [unassignedChats, activity]);

  const handleRename = (chatId: string, title: string) => {
    setEditingChat(chatId);
    setEditTitle(title);
  };

  const handleSaveRename = (chatId: string) => {
    const trimmed = editTitle.trim();
    if (trimmed) {
      onRenameChat(chatId, trimmed);
    }
    setEditingChat(null);
    setEditTitle('');
  };

  const renderChatRow = (chat: SidebarChatItem) => {
    const isActive = currentChatId === chat.id;
    const isDragging = drag.draggedThreadId === chat.id;

    return (
      <li
        key={chat.id}
        draggable={editingChat !== chat.id}
        onDragStart={(e) => drag.handleDragStart(e, chat.id)}
        onDragEnd={drag.handleDragEnd}
        className={cn(
          'relative group rounded-lg transition-colors',
          isActive ? 'bg-secondary text-foreground' : 'hover:bg-secondary/50',
          isDragging && 'opacity-50',
        )}
      >
        {editingChat === chat.id ? (
          <div className="flex items-center gap-2 px-2.5 py-2">
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={() => handleSaveRename(chat.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveRename(chat.id);
                if (e.key === 'Escape') {
                  setEditingChat(null);
                  setEditTitle('');
                }
              }}
              aria-label={t('sidebar.renameChat', { title: chat.title })}
              className="flex-1 bg-transparent text-sm text-foreground border border-border rounded px-1.5 py-0.5 outline-none focus:border-primary"
              autoFocus
            />
          </div>
        ) : (
          <>
            {selecting && (
              <input
                type="checkbox"
                className="absolute left-2 top-1/2 -translate-y-1/2 z-10"
                checked={selection.isSelected(chat.id)}
                onChange={() => selection.toggle(chat.id)}
                aria-label={`Select ${chat.title}`}
              />
            )}
            <button
              type="button"
              onClick={() => (selecting ? selection.toggle(chat.id) : onSelectChat(chat.id))}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'w-full text-left text-sm px-3 py-2.5 pr-24 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                selecting && 'pl-8',
                isActive ? 'text-foreground' : 'text-foreground/70 hover:text-foreground',
              )}
            >
              {/* The dot carries this. A second row naming the running
                  subagent pushed the list item to two lines, moved
                  every row below it, and repeated what the transcript
                  already shows in full. Which subagent is working is
                  detail for the conversation, not the index of it. */}
              <span className="flex items-center gap-2 min-w-0">
                <ChatStatusDot activity={activity[chat.id] ?? 'idle'} />
                <ChatRowTitle title={chat.title} />
              </span>
            </button>

            <div className="absolute right-1.5 top-1/2 -translate-y-1/2 flex gap-0.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
              {onAssignThread &&
              chat.project_id &&
              knownProjectIds.has(chat.project_id) ? (
                <Button
                  variant="plain"
                  size="sm"
                  className="h-7 w-7 !p-0 text-muted-foreground hover:text-foreground focus-visible:opacity-100"
                  onClick={() => void onAssignThread(chat.id, null)}
                  aria-label={t('sidebar.unassignChat', { title: chat.title })}
                >
                  <FolderMinus className="w-3 h-3" />
                </Button>
              ) : onAssignThread && projects.length > 0 ? (
                <Dropdown
                  isOpen={assignMenuChatId === chat.id}
                  onOpenChange={(open) => setAssignMenuChatId(open ? chat.id : null)}
                  onSelect={(_event, value) => {
                    if (typeof value === 'string') {
                      void onAssignThread(chat.id, value);
                    }
                    setAssignMenuChatId(null);
                  }}
                  popperProps={{ position: 'right' }}
                  toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                    <MenuToggle
                      ref={toggleRef}
                      variant="plain"
                      onClick={() =>
                        setAssignMenuChatId((id) => (id === chat.id ? null : chat.id))
                      }
                      isExpanded={assignMenuChatId === chat.id}
                      aria-label={`Add to project: ${chat.title}`}
                      icon={<FolderPlus className="w-3 h-3" />}
                      className="h-7 w-7 !p-0 text-muted-foreground hover:text-foreground"
                    />
                  )}
                >
                  <DropdownList>
                    {projects.map((project) => (
                      <DropdownItem key={project.id} value={project.id}>
                        {project.name}
                      </DropdownItem>
                    ))}
                  </DropdownList>
                </Dropdown>
              ) : null}
              <Button
                variant="plain"
                size="sm"
                className="h-7 w-7 !p-0 text-muted-foreground hover:text-foreground focus-visible:opacity-100"
                onClick={() => onTogglePin?.(chat.id, !chat.pinned)}
                aria-label={
                  chat.pinned
                    ? t('sidebar.unpinChat', { title: chat.title })
                    : t('sidebar.pinChat', { title: chat.title })
                }
              >
                {chat.pinned ? <PinOff className="w-3 h-3" /> : <Pin className="w-3 h-3" />}
              </Button>
              <Button
                variant="plain"
                size="sm"
                className="h-7 w-7 !p-0 text-muted-foreground hover:text-foreground focus-visible:opacity-100"
                onClick={() => handleRename(chat.id, chat.title)}
                aria-label={t('sidebar.renameChat', { title: chat.title })}
              >
                <Edit3 className="w-3 h-3" />
              </Button>
              <Button
                variant="plain"
                size="sm"
                className="h-7 w-7 !p-0 text-muted-foreground hover:text-destructive focus-visible:opacity-100"
                onClick={() => setDeletingChatId(chat.id)}
                aria-label={t('sidebar.deleteChatNamed', { title: chat.title })}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          </>
        )}
      </li>
    );
  };

  const deletingThreadCount =
    projects.find((p) => p.id === deletingProjectId)?.threadCount ?? 0;

  return (
    <div className="flex flex-col h-full min-h-0 bg-sidebar border-r border-sidebar-border text-sidebar-foreground">
      <div className="shrink-0 p-3 pb-2">
        <Button variant="primary" isBlock onClick={() => onNewChat()} aria-label={t('sidebar.startNewChat')} icon={<Plus className="w-4 h-4" />}>
          {/* The label only. `'New Chat'` is also a thread *title*
              sentinel that AppLayout and ChatPage compare against to
              decide when to replace a placeholder title — translating
              that would silently stop titles updating. */}
          {t('sidebar.newChat')}
        </Button>
        {/* Rooms sit beside New chat rather than inside Settings:
            a space is somewhere work happens, not a preference. */}
        <button
          type="button"
          onClick={() => navigate('/spaces')}
          className="mt-2 w-full rounded px-2 py-1 text-left text-sm text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
        >
          {t('sidebar.spaces')}
        </button>
        {/* Scheduled sits here for the same reason Rooms does: it is
            work the agent is going to do, not a setting. */}
        <button
          type="button"
          onClick={() => navigate('/scheduled')}
          className="mt-1 flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
        >
          <Clock className="w-4 h-4" />
          {t('sidebar.scheduled')}
        </button>
        <button
          type="button"
          onClick={() => navigate('/projects')}
          className="mt-1 flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
        >
          <Folder className="w-4 h-4" />
          {t('sidebar.projectsNav')}
        </button>
        {/* Customize is /settings under the name the panel uses.
            One screen, not two: a second settings page would be a
            second place for the same preferences to disagree. */}
        <button
          type="button"
          onClick={() => navigate('/settings')}
          className="mt-1 flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
        >
          <Sliders className="w-4 h-4" />
          {t('sidebar.customize')}
        </button>
      </div>

      {chatHistory.length > 3 && (
        <div className="shrink-0 px-3 py-1.5">
          <SearchInput
            placeholder={t('sidebar.searchThreads')}
            aria-label={t('sidebar.searchChatThreads')}
            value={searchQuery}
            onChange={(_e, value) => setSearchQuery(value)}
          />
        </div>
      )}

      <div className="flex-1 min-h-0 overflow-y-auto chat-scroll">

        <div
          onDragOver={(e) => drag.handleDragOver(e, 'unassigned')}
          onDragLeave={drag.handleDragLeave}
          onDrop={(e) => void drag.handleDrop(e, null)}
          className={cn(
            'rounded-lg mx-1.5 transition-colors',
            drag.dragOverTarget === 'unassigned' && 'ring-2 ring-primary/50 bg-primary/5',
          )}
        >
          <TagFilter onFilter={(_tag, ids) => setTaggedIds(ids)} />

          <div className="shrink-0 px-3 pt-5 pb-2 flex items-center justify-between">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{t('sidebar.chats')}</p>
            {unassignedChats.length > 0 && (
              <button
                type="button"
                className="text-[11px] text-muted-foreground hover:text-foreground"
                aria-pressed={selecting}
                onClick={() => {
                  selection.clear();
                  setSelecting((on) => !on);
                }}
              >
                {selecting ? t('sidebar.doneSelecting') : t('sidebar.selectChats')}
              </button>
            )}
          </div>

          {selecting && (
            <ThreadSelectionBar
              count={selection.count}
              summary={selection.summary}
              beyondThisPage={selection.beyondThisPage}
              onSelectAll={selection.selectAll}
              onClear={() => {
                selection.clear();
                setSelecting(false);
              }}
              onDelete={() => {
                void (async () => {
                  const ids = await idsToDelete({
                    beyondThisPage: selection.beyondThisPage,
                    pickedOnPage: selection.pickedOnPage,
                    targets: selection.targets,
                    listAll: listAllThreadIds,
                  });
                  if (onDeleteMany) {
                    await onDeleteMany(ids);
                  } else {
                    for (const id of ids) onDeleteChat(id);
                  }
                  selection.clear();
                  setSelecting(false);
                })();
              }}
            />
          )}

          {unassignedChats.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
              <MessageSquare className="w-6 h-6 text-muted-foreground/40 mb-2" aria-hidden="true" />
              <p className="text-sm text-muted-foreground">
                {t(
                  `sidebar.${emptyListReason({
                    total: chatHistory.length,
                    searching: searchQuery.trim() !== '',
                  })}`,
                )}
              </p>
            </div>
          ) : (
            <ul
              aria-label={t('sidebar.chatHistory')}
              className="px-0 space-y-1 list-none pb-3"
            >
              {unassignedSections.map(({ key, labelKey, chats }) => (
                <li key={key} className="list-none">
                  {/* Only a section that has something in it. An empty
                      "Ready" heading is a question the reader has to
                      answer by reading nothing. */}
                  <p
                    data-testid={`sidebar-section-${key}`}
                    className="px-3 pt-2 pb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground"
                  >
                    {t(labelKey)}{' '}
                    {/* No `opacity-70` here: muted-foreground at 70% is
                        3.44:1 on the sidebar background, under the 4.5:1
                        WCAG AA minimum for 11px text. */}
                    <span className="tabular-nums">{chats.length}</span>
                  </p>
                  <ul className="px-0 space-y-1 list-none">
                    {chats.map((chat) => renderChatRow(chat))}
                  </ul>
                </li>
              ))}
            </ul>
          )}

          {searchQuery.trim() && (
            <SearchResults
              hits={contentSearch.hits}
              loading={contentSearch.loading}
              error={contentSearch.error}
              excludeIds={locallyMatched}
              onSelect={onSelectChat}
            />
          )}
        </div>
      </div>

      <div className="shrink-0 px-3 py-3 border-t border-sidebar-border">
        <Tooltip
          content={t(`sidebar.agent.${agentHealth.status}`)}
        >
          <div className="flex items-center gap-2 text-xs text-muted-foreground cursor-default">
            <span
              className={cn(
                'h-2 w-2 rounded-full shrink-0',
                agentHealth.status === 'healthy' && 'bg-green-500',
                // Amber, not red: it is still answering.
                agentHealth.status === 'degraded' && 'bg-amber-500',
                agentHealth.status === 'unhealthy' && 'bg-red-500',
                agentHealth.status === 'unknown' && 'bg-gray-400',
              )}
              aria-hidden
            />
            <span className="truncate">
              {t(`sidebar.agent.${agentHealth.status}`)}
            </span>
          </div>
        </Tooltip>
      </div>

      <div className="shrink-0 p-3 border-t border-sidebar-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center text-sm font-semibold text-primary">
            {userName.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{userName}</p>
          </div>
          {/* Settings and sign out only.
              Every operator surface — Usage, Feature flags, Skills,
              Documents — is a tab inside Settings, so putting a
              shortcut to each one beside the user name grew a row of
              icons that said nothing about the person they sat next
              to. One door into Settings, one way out. */}
          <button
            type="button"
            onClick={() => navigate('/settings')}
            className="shrink-0 p-1.5 rounded-lg text-muted-foreground hover:bg-secondary/50 hover:text-foreground transition-colors cursor-pointer"
            aria-label={t('sidebar.openSettings')}
          >
            <Settings className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => {
              void logout();
            }}
            className="shrink-0 p-1.5 rounded-lg text-muted-foreground hover:bg-secondary/50 hover:text-foreground transition-colors cursor-pointer"
            aria-label={t('sidebar.logOut')}
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      <Modal
        variant={ModalVariant.small}
        isOpen={deletingChatId !== null}
        onClose={() => setDeletingChatId(null)}
        aria-label={t('sidebar.deleteChatConfirm')}
      >
        <ModalHeader title={t('sidebar.deleteChat')} />
        <ModalBody>{t('sidebar.deleteChatBody')}</ModalBody>
        <ModalFooter>
          <Button
            variant="danger"
            onClick={() => {
              if (deletingChatId) {
                onDeleteChat(deletingChatId);
                setDeletingChatId(null);
              }
            }}
          >
            {t('common.delete')}
          </Button>
          <Button variant="link" onClick={() => setDeletingChatId(null)}>
            {t('common.cancel')}
          </Button>
        </ModalFooter>
      </Modal>

      <Modal
        variant={ModalVariant.small}
        isOpen={deletingProjectId !== null}
        onClose={() => {
          if (!projectDeleteBusy) setDeletingProjectId(null);
        }}
        aria-label={t('sidebar.deleteProjectConfirm')}
      >
        <ModalHeader title={t('sidebar.deleteProject')} />
        <ModalBody>
          {t('sidebar.deleteProjectBody')}
          {deletingThreadCount > 0 && (
            <p className="mt-2 text-sm text-muted-foreground">
              {t('sidebar.keepConversationsHint')}
            </p>
          )}
        </ModalBody>
        <ModalFooter>
          {deletingThreadCount > 0 && (
            <Button
              variant="secondary"
              isDisabled={projectDeleteBusy}
              onClick={() => {
                if (!deletingProjectId) return;
                void (async () => {
                  setProjectDeleteBusy(true);
                  try {
                    const ok = await onDeleteProject?.(deletingProjectId, {
                      keepThreads: true,
                    });
                    if (ok) setDeletingProjectId(null);
                  } finally {
                    setProjectDeleteBusy(false);
                  }
                })();
              }}
            >
              {t('sidebar.unassignAndDelete')}
            </Button>
          )}
          <Button
            variant="danger"
            isDisabled={projectDeleteBusy}
            onClick={() => {
              if (!deletingProjectId) return;
              void (async () => {
                setProjectDeleteBusy(true);
                try {
                  const ok = await onDeleteProject?.(deletingProjectId);
                  if (ok) setDeletingProjectId(null);
                } finally {
                  setProjectDeleteBusy(false);
                }
              })();
            }}
          >
            Delete
          </Button>
          <Button
            variant="link"
            isDisabled={projectDeleteBusy}
            onClick={() => setDeletingProjectId(null)}
          >
            Cancel
          </Button>
        </ModalFooter>
      </Modal>

      <Modal
        variant={ModalVariant.small}
        isOpen={unassigningProjectId !== null}
        onClose={() => {
          if (!unassignBusy) setUnassigningProjectId(null);
        }}
        aria-label={t('sidebar.unassignAllConfirm')}
      >
        <ModalHeader title={t('sidebar.unassignAll')} />
        <ModalBody>{t('sidebar.unassignAllBody')}</ModalBody>
        <ModalFooter>
          <Button
            variant="danger"
            isDisabled={unassignBusy}
            onClick={() => {
              if (!unassigningProjectId || !onUnassignAll) return;
              void (async () => {
                setUnassignBusy(true);
                try {
                  const ok = await onUnassignAll(unassigningProjectId);
                  if (ok) setUnassigningProjectId(null);
                } finally {
                  setUnassignBusy(false);
                }
              })();
            }}
          >
            {t('sidebar.unassign')}
          </Button>
          <Button
            variant="link"
            isDisabled={unassignBusy}
            onClick={() => setUnassigningProjectId(null)}
          >
            {t('common.cancel')}
          </Button>
        </ModalFooter>
      </Modal>

      <ProjectEditModal
        isOpen={projectModalOpen}
        onClose={() => {
          setProjectModalOpen(false);
          setEditingProject(null);
        }}
        title={editingProject ? t('sidebar.editProject') : t('sidebar.newProject')}
        initialName={editingProject?.name ?? ''}
        initialDescription={editingProject?.description ?? ''}
        onSave={async (name, description) => {
          const taken = projects.some(
            (p) =>
              p.name.trim().toLowerCase() === name.toLowerCase() &&
              p.id !== editingProject?.id,
          );
          if (taken) return false;

          try {
            if (editingProject) {
              const ok = await onUpdateProject?.(editingProject.id, name, description);
              return ok !== false;
            }
            const id = await onCreateProject?.(name, description);
            if (!id) return false;
            navigate(`/project/${id}`);
            return true;
          } catch {
            return 'error';
          }
        }}
      />
    </div>
  );
}

export const Sidebar = React.memo(SidebarComponent);
