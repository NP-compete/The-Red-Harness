import type { Message } from "@langchain/langgraph-sdk";
import { ProcessedEvent } from "../components/ActivityTimeline";

export interface ChatItem {
  id: string;
  title: string;
  timestamp?: Date;
  preview: string;
  /** The agent's last word on this conversation's run. */
  serverStatus?: string | null;
  messages: Message[];
  historicalActivities?: Record<string, ProcessedEvent[]>;
  feedback?: Record<string, 'up' | 'down'>;
  project_id?: string | null;
  /** Kept at the top of the sidebar, for this person, everywhere. */
  pinned?: boolean;
}

export interface ChatState {
  chats: ChatItem[];
  isLoading: boolean;
  error: string | null;
}

export interface ChatActions {
  createNewChat: () => string;
  deleteChat: (chatId: string) => void;
  renameChat: (chatId: string, newTitle: string) => void;
  updateChatMessages: (chatId: string, messages: Message[]) => void;
  updateChatActivities: (chatId: string, messageId: string, activities: ProcessedEvent[]) => void;
  clearError: () => void;
  setError: (error: string) => void;
  getChatById: (chatId: string) => ChatItem | undefined;
}

export interface ChatContextType extends ChatState, ChatActions {}

export interface SidebarChatItem {
  id: string;
  title: string;
  timestamp: Date;
  preview: string;
  project_id?: string | null;
  /** Pinned conversations lead the list, ahead of run state. */
  pinned?: boolean;
}

// The agent owns this shape, so it comes from the generated
// contract rather than being described twice (E10-T14).
export type { Project } from './contract';

export interface SidebarProject {
  id: string;
  name: string;
  description: string | null;
  threadCount: number;
}
