"use client";

import React, {
  createContext,
  useContext,
  useRef,
  useState,
  useCallback,
} from "react";
import { wsUrl, apiUrl } from "@/lib/api";
import { ChatState, HomeChatMessage, INITIAL_CHAT_STATE } from "@/types/chat";

// Context type
interface ChatContextType {
  chatState: ChatState;
  setChatState: React.Dispatch<React.SetStateAction<ChatState>>;
  sendChatMessage: (message: string) => void;
  clearChatHistory: () => void;
  loadChatSession: (sessionId: string) => Promise<void>;
  newChatSession: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [chatState, setChatState] = useState<ChatState>(INITIAL_CHAT_STATE);
  const chatWs = useRef<WebSocket | null>(null);
  // Use ref to always have the latest sessionId in WebSocket callbacks
  const sessionIdRef = useRef<string | null>(null);

  const sendChatMessage = useCallback(
    (message: string) => {
      if (!message.trim() || chatState.isLoading) return;

      // Add user message
      setChatState((prev) => ({
        ...prev,
        isLoading: true,
        currentStage: "connecting",
        messages: [...prev.messages, { role: "user", content: message }],
      }));

      // Close existing connection if any
      if (chatWs.current) {
        chatWs.current.close();
      }

      const ws = new WebSocket(wsUrl("/api/v1/chat"));
      chatWs.current = ws;

      let assistantMessage = "";

      ws.onopen = () => {
        // Build history from current messages (excluding the one just added)
        const history = chatState.messages.map((msg) => ({
          role: msg.role,
          content: msg.content,
        }));

        ws.send(
          JSON.stringify({
            message,
            session_id: sessionIdRef.current,
            history,
            kb_name: chatState.selectedKb,
            enable_rag: chatState.enableRag,
            enable_web_search: chatState.enableWebSearch,
          }),
        );
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "session") {
          sessionIdRef.current = data.session_id;
          setChatState((prev) => ({
            ...prev,
            sessionId: data.session_id,
          }));
        } else if (data.type === "status") {
          setChatState((prev) => ({
            ...prev,
            currentStage: data.stage || data.message,
          }));
        } else if (data.type === "stream") {
          assistantMessage += data.content;
          setChatState((prev) => {
            const messages = [...prev.messages];
            const lastMessage = messages[messages.length - 1];
            if (lastMessage?.role === "assistant" && lastMessage?.isStreaming) {
              messages[messages.length - 1] = {
                ...lastMessage,
                content: assistantMessage,
              };
            } else {
              messages.push({
                role: "assistant",
                content: assistantMessage,
                isStreaming: true,
              });
            }
            return { ...prev, messages, currentStage: "generating" };
          });
        } else if (data.type === "sources") {
          setChatState((prev) => {
            const messages = [...prev.messages];
            const lastMessage = messages[messages.length - 1];
            if (lastMessage?.role === "assistant") {
              messages[messages.length - 1] = {
                ...lastMessage,
                sources: { rag: data.rag, web: data.web },
              };
            }
            return { ...prev, messages };
          });
        } else if (data.type === "result") {
          setChatState((prev) => {
            const messages = [...prev.messages];
            const lastMessage = messages[messages.length - 1];
            if (lastMessage?.role === "assistant") {
              messages[messages.length - 1] = {
                ...lastMessage,
                content: data.content,
                isStreaming: false,
              };
            }
            return {
              ...prev,
              messages,
              isLoading: false,
              currentStage: null,
            };
          });
          ws.close();
        } else if (data.type === "error") {
          setChatState((prev) => ({
            ...prev,
            isLoading: false,
            currentStage: null,
            messages: [
              ...prev.messages,
              { role: "assistant", content: `Error: ${data.message}` },
            ],
          }));
          ws.close();
        }
      };

      ws.onerror = () => {
        setChatState((prev) => ({
          ...prev,
          isLoading: false,
          currentStage: null,
          messages: [
            ...prev.messages,
            {
              role: "assistant",
              content: "Connection error. Please try again.",
            },
          ],
        }));
      };

      ws.onclose = () => {
        if (chatWs.current === ws) {
          chatWs.current = null;
        }
        setChatState((prev) => ({
          ...prev,
          isLoading: false,
          currentStage: null,
        }));
      };
    },
    [
      chatState.isLoading,
      chatState.messages,
      chatState.selectedKb,
      chatState.enableRag,
      chatState.enableWebSearch,
    ],
  );

  const clearChatHistory = useCallback(() => {
    sessionIdRef.current = null;
    setChatState((prev) => ({
      ...prev,
      sessionId: null,
      messages: [],
      currentStage: null,
    }));
  }, []);

  const newChatSession = useCallback(() => {
    if (chatWs.current) {
      chatWs.current.close();
      chatWs.current = null;
    }
    sessionIdRef.current = null;
    setChatState((prev) => ({
      ...prev,
      sessionId: null,
      messages: [],
      isLoading: false,
      currentStage: null,
    }));
  }, []);

  const loadChatSession = useCallback(async (sessionId: string) => {
    try {
      const response = await fetch(
        apiUrl(`/api/v1/chat/sessions/${sessionId}`),
      );
      if (!response.ok) {
        throw new Error("Session not found");
      }
      const session = await response.json();

      const messages: HomeChatMessage[] = session.messages.map((msg: any) => ({
        role: msg.role,
        content: msg.content,
        sources: msg.sources,
        isStreaming: false,
      }));

      const settings = session.settings || {};

      sessionIdRef.current = session.session_id;

      setChatState((prev) => ({
        ...prev,
        sessionId: session.session_id,
        messages,
        selectedKb: settings.kb_name || prev.selectedKb,
        enableRag: settings.enable_rag ?? prev.enableRag,
        enableWebSearch: settings.enable_web_search ?? prev.enableWebSearch,
        isLoading: false,
        currentStage: null,
      }));
    } catch (error) {
      console.error("Failed to load session:", error);
      throw error;
    }
  }, []);

  return (
    <ChatContext.Provider
      value={{
        chatState,
        setChatState,
        sendChatMessage,
        clearChatHistory,
        loadChatSession,
        newChatSession,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) throw new Error("useChat must be used within ChatProvider");
  return context;
};
