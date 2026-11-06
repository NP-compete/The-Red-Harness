import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test-utils/render';
import { Sidebar } from './Sidebar';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const sidebarProps = {
  chatHistory: [],
  onNewChat: vi.fn(),
  onSelectChat: vi.fn(),
  onDeleteChat: vi.fn(),
  onRenameChat: vi.fn(),
};

describe('Sidebar — activity grouping', () => {
  const chat = (id: string, title: string) => ({
    id,
    title,
    timestamp: new Date().toISOString(),
    preview: '',
    messages: [],
  });

  const blankStream = {
    isLoading: false,
    isThinking: false,
    isConnected: true,
    error: null,
    currentRunId: null,
    pendingInterrupt: null,
    taskSteps: [],
    isReconnecting: false,
    reconnectAttempt: 0,
    streamDroppedMidResponse: false,
  };

  function renderSidebar() {
    return renderWithProviders(
      <Sidebar
        {...sidebarProps}
        chatHistory={[
          chat('running-1', 'Quarterly numbers'),
          chat('blocked-1', 'Delete the staging table'),
          chat('done-1', 'Yesterday chat'),
        ]}
      />,
      {
        preloadedState: {
          chats: {
            chats: [],
            streamingStates: {
              'running-1': { ...blankStream, isLoading: true },
              'blocked-1': { ...blankStream, pendingInterrupt: { value: 'approve?' } },
            },
            error: null,
            loadingThreads: false,
            threadsListHydrated: true,
            messageFeedback: {},
          },
        },
      },
    );
  }

  it('groups chats by what they need from the reader', () => {
    renderSidebar();

    expect(screen.getByTestId('sidebar-section-needs-input')).toHaveTextContent('1');
    expect(screen.getByTestId('sidebar-section-running')).toHaveTextContent('1');
    expect(screen.getByTestId('sidebar-section-idle')).toHaveTextContent('1');
  });

  it('marks a running chat green and a blocked one yellow', () => {
    renderSidebar();

    expect(screen.getByTestId('chat-status-running')).toBeInTheDocument();
    expect(screen.getByTestId('chat-status-needs-input')).toBeInTheDocument();
  });

  it('shows no dot and no empty headings when nothing is active', () => {
    renderWithProviders(
      <Sidebar {...sidebarProps} chatHistory={[chat('done-1', 'Yesterday chat')]} />,
    );

    expect(screen.queryByTestId('chat-status-running')).not.toBeInTheDocument();
    expect(screen.queryByTestId('sidebar-section-needs-input')).not.toBeInTheDocument();
    expect(screen.queryByTestId('sidebar-section-running')).not.toBeInTheDocument();
    // The one remaining group still renders, holding the finished chat.
    expect(screen.getByTestId('sidebar-section-idle')).toBeInTheDocument();
  });
});
