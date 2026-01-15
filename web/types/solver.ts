// Solver-specific types

import { LogEntry, AgentStatus, TokenStats } from "./common";

/**
 * Chat message in solver conversation
 */
export interface SolverChatMessage {
  role: "user" | "assistant";
  content: string;
  outputDir?: string;
}

/**
 * Solver progress information
 */
export interface SolverProgressInfo {
  stage: "investigate" | "solve" | "response" | null;
  progress: {
    round?: number;
    queries?: string[];
    step_index?: number;
    step_id?: string;
    step_target?: string;
  };
}

/**
 * Solver state
 */
export interface SolverState {
  isSolving: boolean;
  logs: LogEntry[];
  messages: SolverChatMessage[];
  question: string;
  selectedKb: string;
  agentStatus: AgentStatus;
  tokenStats: TokenStats;
  progress: SolverProgressInfo;
}

/**
 * Default agent status for solver
 */
export const DEFAULT_SOLVER_AGENT_STATUS: AgentStatus = {
  InvestigateAgent: "pending",
  NoteAgent: "pending",
  ManagerAgent: "pending",
  SolveAgent: "pending",
  ToolAgent: "pending",
  ResponseAgent: "pending",
  PrecisionAnswerAgent: "pending",
};

/**
 * Default token stats
 */
export const DEFAULT_TOKEN_STATS: TokenStats = {
  model: "Unknown",
  calls: 0,
  tokens: 0,
  input_tokens: 0,
  output_tokens: 0,
  cost: 0.0,
};

/**
 * Initial solver state
 */
export const INITIAL_SOLVER_STATE: SolverState = {
  isSolving: false,
  logs: [],
  messages: [],
  question: "",
  selectedKb: "",
  agentStatus: DEFAULT_SOLVER_AGENT_STATUS,
  tokenStats: DEFAULT_TOKEN_STATS,
  progress: {
    stage: null,
    progress: {},
  },
};
