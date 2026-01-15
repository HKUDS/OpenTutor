// Chat-specific types for home page chat

/**
 * Source references for chat messages
 */
export interface ChatSource {
  rag?: Array<{ kb_name: string; content: string }>;
  web?: Array<{ url: string; title?: string; snippet?: string }>;
}

/**
 * Chat message with sources and streaming state
 */
export interface HomeChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource;
  isStreaming?: boolean;
}

/**
 * Chat state
 */
export interface ChatState {
  sessionId: string | null;
  messages: HomeChatMessage[];
  isLoading: boolean;
  selectedKb: string;
  enableRag: boolean;
  enableWebSearch: boolean;
  currentStage: string | null;
}

/**
 * Initial chat state
 */
export const INITIAL_CHAT_STATE: ChatState = {
  sessionId: null,
  messages: [],
  isLoading: false,
  selectedKb: "",
  enableRag: false,
  enableWebSearch: false,
  currentStage: null,
};
