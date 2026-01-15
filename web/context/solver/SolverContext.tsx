"use client";

import React, {
  createContext,
  useContext,
  useRef,
  useState,
  useCallback,
} from "react";
import { wsUrl } from "@/lib/api";
import {
  SolverState,
  SolverChatMessage,
  SolverProgressInfo,
  INITIAL_SOLVER_STATE,
  DEFAULT_SOLVER_AGENT_STATUS,
  DEFAULT_TOKEN_STATS,
} from "@/types/solver";
import { LogEntry, AgentStatus, TokenStats } from "@/types/common";

// Context type
interface SolverContextType {
  solverState: SolverState;
  setSolverState: React.Dispatch<React.SetStateAction<SolverState>>;
  startSolver: (question: string, kb: string) => void;
  stopSolver: () => void;
}

const SolverContext = createContext<SolverContextType | undefined>(undefined);

export function SolverProvider({ children }: { children: React.ReactNode }) {
  const [solverState, setSolverState] =
    useState<SolverState>(INITIAL_SOLVER_STATE);
  const solverWs = useRef<WebSocket | null>(null);

  const addSolverLog = useCallback((log: LogEntry) => {
    setSolverState((prev) => ({ ...prev, logs: [...prev.logs, log] }));
  }, []);

  const startSolver = useCallback(
    (question: string, kb: string) => {
      if (solverWs.current) solverWs.current.close();

      setSolverState((prev) => ({
        ...prev,
        isSolving: true,
        logs: [],
        messages: [
          ...prev.messages,
          { role: "user" as const, content: question },
        ],
        question,
        selectedKb: kb,
        agentStatus: { ...DEFAULT_SOLVER_AGENT_STATUS },
        tokenStats: { ...DEFAULT_TOKEN_STATS },
        progress: {
          stage: null,
          progress: {},
        },
      }));

      const ws = new WebSocket(wsUrl("/api/v1/solve"));
      solverWs.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ question, kb_name: kb }));
        addSolverLog({ type: "system", content: "Initializing connection..." });
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "log") {
          addSolverLog(data);
        } else if (data.type === "agent_status") {
          setSolverState((prev) => ({
            ...prev,
            agentStatus: data.all_agents || {
              ...prev.agentStatus,
              [data.agent]: data.status,
            },
          }));
        } else if (data.type === "token_stats") {
          setSolverState((prev) => ({
            ...prev,
            tokenStats: data.stats || prev.tokenStats,
          }));
        } else if (data.type === "progress") {
          setSolverState((prev) => ({
            ...prev,
            progress: {
              stage: data.stage,
              progress: data.progress || {},
            },
          }));
        } else if (data.type === "result") {
          // Extract relative path from output_dir
          let dirName = "";
          if (data.output_dir) {
            const parts = data.output_dir.split(/[/\\]/);
            dirName = parts[parts.length - 1];
          }

          setSolverState((prev) => ({
            ...prev,
            messages: [
              ...prev.messages,
              {
                role: "assistant" as const,
                content: data.final_answer,
                outputDir: dirName,
              },
            ],
            isSolving: false,
          }));
          ws.close();
        } else if (data.type === "error") {
          addSolverLog({
            type: "error",
            content: `Error: ${data.content || data.message || "Unknown error"}`,
          });
          setSolverState((prev) => ({ ...prev, isSolving: false }));
        }
      };

      ws.onerror = () => {
        addSolverLog({ type: "error", content: "Connection error" });
        setSolverState((prev) => ({
          ...prev,
          isSolving: false,
          agentStatus: {
            InvestigateAgent: "error",
            NoteAgent: "error",
            ManagerAgent: "error",
            SolveAgent: "error",
            ToolAgent: "error",
            ResponseAgent: "error",
            PrecisionAnswerAgent: "error",
          },
          progress: {
            stage: null,
            progress: {},
          },
        }));
      };

      ws.onclose = () => {
        if (solverWs.current === ws) {
          solverWs.current = null;
        }
      };
    },
    [addSolverLog],
  );

  const stopSolver = useCallback(() => {
    if (solverWs.current) {
      solverWs.current.close();
      solverWs.current = null;
    }
    setSolverState((prev) => ({
      ...prev,
      isSolving: false,
    }));
    addSolverLog({ type: "system", content: "Solver stopped by user." });
  }, [addSolverLog]);

  return (
    <SolverContext.Provider
      value={{
        solverState,
        setSolverState,
        startSolver,
        stopSolver,
      }}
    >
      {children}
    </SolverContext.Provider>
  );
}

export const useSolver = () => {
  const context = useContext(SolverContext);
  if (!context) throw new Error("useSolver must be used within SolverProvider");
  return context;
};
