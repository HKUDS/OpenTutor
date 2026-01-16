/**
 * useSolverSession - Hook for managing solver session persistence
 *
 * This hook provides:
 * - Auto-loading of active session on mount
 * - Auto-saving of messages as they change
 * - Session CRUD operations
 * - localStorage fallback for offline support
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { apiUrl } from "@/lib/api";

// Types
export interface SolverMessage {
  role: "user" | "assistant";
  content: string;
  output_dir?: string | null;
  timestamp?: string;
}

export interface TokenStats {
  model: string;
  calls: number;
  tokens: number;
  input_tokens: number;
  output_tokens: number;
  cost: number;
}

export interface SolverSession {
  id: string;
  title: string;
  knowledge_base: string;
  messages: SolverMessage[];
  token_stats: TokenStats;
  created_at: string;
  updated_at: string;
  is_active: boolean;
  message_count: number;
}

interface UseSolverSessionOptions {
  autoSave?: boolean; // Save on each message change (default: true)
  autoLoad?: boolean; // Load active session on mount (default: true)
  debounceMs?: number; // Debounce save calls (default: 1000)
}

const STORAGE_KEY = "deeptutor-solver-session";

// Helper to debounce function calls
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

export function useSolverSession(options: UseSolverSessionOptions = {}) {
  const { autoSave = true, autoLoad = true, debounceMs = 1000 } = options;

  const [session, setSession] = useState<SolverSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const lastMessagesRef = useRef<string>("");

  // Load session from localStorage cache
  const loadFromCache = useCallback((): SolverSession | null => {
    try {
      const cached = localStorage.getItem(STORAGE_KEY);
      if (cached) {
        return JSON.parse(cached);
      }
    } catch (e) {
      console.warn("Failed to load session from cache:", e);
    }
    return null;
  }, []);

  // Save session to localStorage cache
  const saveToCache = useCallback((session: SolverSession) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } catch (e) {
      console.warn("Failed to save session to cache:", e);
    }
  }, []);

  // Clear localStorage cache
  const clearCache = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      console.warn("Failed to clear session cache:", e);
    }
  }, []);

  // Load active session from backend
  const loadActiveSession = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(apiUrl("/api/v1/solver/sessions/active"));
      if (response.ok) {
        const data = await response.json();
        if (data) {
          setSession(data);
          saveToCache(data);
          lastMessagesRef.current = JSON.stringify(data.messages);
          return data;
        }
      }

      // No active session from backend, try cache
      const cached = loadFromCache();
      if (cached) {
        setSession(cached);
        lastMessagesRef.current = JSON.stringify(cached.messages);
        return cached;
      }

      setSession(null);
      return null;
    } catch (e) {
      console.error("Failed to load active session:", e);
      setError("Failed to load session");

      // Fallback to cache
      const cached = loadFromCache();
      if (cached) {
        setSession(cached);
        lastMessagesRef.current = JSON.stringify(cached.messages);
        return cached;
      }
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [loadFromCache, saveToCache]);

  // Create a new session
  const createSession = useCallback(
    async (knowledgeBase: string = ""): Promise<SolverSession | null> => {
      try {
        const response = await fetch(apiUrl("/api/v1/solver/sessions"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ knowledge_base: knowledgeBase }),
        });

        if (response.ok) {
          const data = await response.json();
          setSession(data);
          saveToCache(data);
          lastMessagesRef.current = JSON.stringify(data.messages);
          return data;
        }

        throw new Error("Failed to create session");
      } catch (e) {
        console.error("Failed to create session:", e);
        setError("Failed to create session");
        return null;
      }
    },
    [saveToCache],
  );

  // Add a message to the current session
  const addMessage = useCallback(
    async (
      role: "user" | "assistant",
      content: string,
      outputDir?: string,
    ): Promise<SolverSession | null> => {
      if (!session) {
        console.warn("No active session to add message to");
        return null;
      }

      try {
        const response = await fetch(
          apiUrl(`/api/v1/solver/sessions/${session.id}/messages`),
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ role, content, output_dir: outputDir }),
          },
        );

        if (response.ok) {
          const data = await response.json();
          setSession(data);
          saveToCache(data);
          lastMessagesRef.current = JSON.stringify(data.messages);
          return data;
        }

        throw new Error("Failed to add message");
      } catch (e) {
        console.error("Failed to add message:", e);

        // Optimistic update for offline support
        const updatedSession = {
          ...session,
          messages: [
            ...session.messages,
            {
              role,
              content,
              output_dir: outputDir || null,
              timestamp: new Date().toISOString(),
            },
          ],
          message_count: session.message_count + 1,
        };
        setSession(updatedSession);
        saveToCache(updatedSession);
        return updatedSession;
      }
    },
    [session, saveToCache],
  );

  // Update token stats
  const updateTokenStats = useCallback(
    async (stats: Partial<TokenStats>): Promise<void> => {
      if (!session) return;

      try {
        await fetch(
          apiUrl(`/api/v1/solver/sessions/${session.id}/token-stats`),
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(stats),
          },
        );
      } catch (e) {
        console.error("Failed to update token stats:", e);
      }
    },
    [session],
  );

  // Clear the current session (for "New Chat")
  const clearSession = useCallback(async () => {
    clearCache();
    setSession(null);
    lastMessagesRef.current = "";
  }, [clearCache]);

  // Delete a session
  const deleteSession = useCallback(
    async (sessionId: string): Promise<boolean> => {
      try {
        const response = await fetch(
          apiUrl(`/api/v1/solver/sessions/${sessionId}`),
          {
            method: "DELETE",
          },
        );

        if (response.ok) {
          if (session?.id === sessionId) {
            clearCache();
            setSession(null);
          }
          return true;
        }
        return false;
      } catch (e) {
        console.error("Failed to delete session:", e);
        return false;
      }
    },
    [session, clearCache],
  );

  // Load on mount if autoLoad is enabled
  useEffect(() => {
    if (autoLoad) {
      loadActiveSession();
    } else {
      setIsLoading(false);
    }
  }, [autoLoad, loadActiveSession]);

  // Debounced save for auto-save
  const debouncedSave = useCallback(
    debounce(async (sessionToSave: SolverSession) => {
      if (!sessionToSave.id) return;

      try {
        await fetch(apiUrl(`/api/v1/solver/sessions/${sessionToSave.id}`), {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: sessionToSave.title,
            knowledge_base: sessionToSave.knowledge_base,
          }),
        });
      } catch (e) {
        console.error("Failed to auto-save session:", e);
      }
    }, debounceMs),
    [debounceMs],
  );

  // Auto-save when session changes
  useEffect(() => {
    if (autoSave && session) {
      const currentMessages = JSON.stringify(session.messages);
      if (currentMessages !== lastMessagesRef.current) {
        saveToCache(session);
        lastMessagesRef.current = currentMessages;
      }
    }
  }, [autoSave, session, saveToCache]);

  return {
    session,
    isLoading,
    error,
    loadActiveSession,
    createSession,
    addMessage,
    updateTokenStats,
    clearSession,
    deleteSession,
    setSession,
  };
}

export default useSolverSession;
