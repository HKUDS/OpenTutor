// Guide page types

export interface Notebook {
  id: string;
  name: string;
  description: string;
  record_count: number;
  color: string;
}

export interface NotebookRecord {
  id: string;
  title: string;
  user_query: string;
  output: string;
  type: string;
}

export interface SelectedRecord extends NotebookRecord {
  notebookId: string;
  notebookName: string;
}

export interface KnowledgePoint {
  knowledge_title: string;
  knowledge_summary: string;
  user_difficulty: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: number;
}

export interface SessionState {
  session_id: string | null;
  notebook_id: string | null;
  notebook_name: string;
  knowledge_points: KnowledgePoint[];
  current_index: number;
  current_html: string;
  status: "idle" | "initialized" | "learning" | "completed";
  progress: number;
  summary: string;
}

export const INITIAL_SESSION_STATE: SessionState = {
  session_id: null,
  notebook_id: null,
  notebook_name: "",
  knowledge_points: [],
  current_index: -1,
  current_html: "",
  status: "idle",
  progress: 0,
  summary: "",
};

// Helper to get record type color
export function getTypeColor(type: string): string {
  switch (type) {
    case "solve":
      return "bg-blue-100 text-blue-700 border-blue-200";
    case "question":
      return "bg-purple-100 text-purple-700 border-purple-200";
    case "research":
      return "bg-emerald-100 text-emerald-700 border-emerald-200";
    case "co_writer":
      return "bg-amber-100 text-amber-700 border-amber-200";
    default:
      return "bg-slate-100 text-slate-700 border-slate-200";
  }
}
