// Shared types used across multiple contexts

/**
 * Generic log entry used by Solver, Question, Research contexts
 */
export interface LogEntry {
  type: string;
  content: string;
  timestamp?: number;
  level?: string;
}

/**
 * Generic agent status mapping
 */
export interface AgentStatus {
  [key: string]: "pending" | "running" | "done" | "error";
}

/**
 * Token usage statistics
 */
export interface TokenStats {
  model: string;
  calls: number;
  tokens: number;
  input_tokens: number;
  output_tokens: number;
  cost: number;
}

/**
 * UI theme type
 */
export type Theme = "light" | "dark";

/**
 * Supported languages
 */
export type Language = "en" | "zh";

/**
 * UI Settings
 */
export interface UISettings {
  theme: Theme;
  language: Language;
}
