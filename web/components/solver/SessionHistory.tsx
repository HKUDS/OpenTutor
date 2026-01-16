/**
 * SessionHistory - Sidebar component showing conversation history
 *
 * Features:
 * - Lists past sessions with titles and timestamps
 * - "New Chat" button to start fresh conversation
 * - Click to switch between sessions
 * - Delete sessions
 */

import { useState, useEffect, useCallback } from "react";
import {
  Plus,
  MessageSquare,
  Trash2,
  Clock,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { apiUrl } from "@/lib/api";

interface Session {
  id: string;
  title: string;
  knowledge_base: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

interface SessionHistoryProps {
  currentSessionId?: string;
  onSelectSession: (sessionId: string) => void;
  onNewSession: () => void;
  className?: string;
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export default function SessionHistory({
  currentSessionId,
  onSelectSession,
  onNewSession,
  className = "",
}: SessionHistoryProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Fetch sessions
  const fetchSessions = useCallback(async () => {
    try {
      const response = await fetch(apiUrl("/api/v1/solver/sessions?limit=20"));
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      }
    } catch (e) {
      console.error("Failed to fetch sessions:", e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Delete session
  const handleDelete = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (deletingId) return;

    setDeletingId(sessionId);
    try {
      const response = await fetch(
        apiUrl(`/api/v1/solver/sessions/${sessionId}`),
        { method: "DELETE" },
      );
      if (response.ok) {
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        if (currentSessionId === sessionId) {
          onNewSession();
        }
      }
    } catch (e) {
      console.error("Failed to delete session:", e);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header with New Chat button */}
      <div className="p-3 border-b border-slate-200 dark:border-slate-700">
        <button
          onClick={onNewSession}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-8 text-slate-400 dark:text-slate-500 text-sm">
            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
            No conversations yet
          </div>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              onClick={() => onSelectSession(session.id)}
              className={`group relative p-3 rounded-lg cursor-pointer transition-colors ${
                currentSessionId === session.id
                  ? "bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700"
                  : "hover:bg-slate-100 dark:hover:bg-slate-800 border border-transparent"
              }`}
            >
              <div className="flex items-start gap-2">
                <MessageSquare
                  className={`w-4 h-4 mt-0.5 shrink-0 ${
                    currentSessionId === session.id
                      ? "text-blue-600 dark:text-blue-400"
                      : "text-slate-400 dark:text-slate-500"
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <div
                    className={`font-medium text-sm truncate ${
                      currentSessionId === session.id
                        ? "text-blue-700 dark:text-blue-300"
                        : "text-slate-700 dark:text-slate-300"
                    }`}
                  >
                    {session.title || "Untitled Chat"}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-slate-400 dark:text-slate-500">
                    <Clock className="w-3 h-3" />
                    <span>{formatTimeAgo(session.updated_at)}</span>
                    <span>•</span>
                    <span>{session.message_count} msgs</span>
                  </div>
                </div>
                <ChevronRight
                  className={`w-4 h-4 shrink-0 transition-opacity ${
                    currentSessionId === session.id
                      ? "text-blue-500 opacity-100"
                      : "text-slate-400 opacity-0 group-hover:opacity-100"
                  }`}
                />
              </div>

              {/* Delete button */}
              <button
                onClick={(e) => handleDelete(e, session.id)}
                disabled={deletingId === session.id}
                className="absolute right-2 top-2 p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/30 text-slate-400 hover:text-red-600 transition-all"
                title="Delete conversation"
              >
                {deletingId === session.id ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
