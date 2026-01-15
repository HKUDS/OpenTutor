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
  ResearchContextState,
  ResearchProgress,
  ActiveTaskInfo,
  QueryInfo,
  INITIAL_RESEARCH_CONTEXT_STATE,
} from "@/types/research";
import { LogEntry } from "@/types/common";

// Context type
interface ResearchContextType {
  researchState: ResearchContextState;
  setResearchState: React.Dispatch<React.SetStateAction<ResearchContextState>>;
  startResearch: (
    topic: string,
    kb: string,
    planMode?: string,
    enabledTools?: string[],
    skipRephrase?: boolean,
  ) => void;
}

const ResearchContext = createContext<ResearchContextType | undefined>(
  undefined,
);

export function ResearchProvider({ children }: { children: React.ReactNode }) {
  const [researchState, setResearchState] = useState<ResearchContextState>(
    INITIAL_RESEARCH_CONTEXT_STATE,
  );
  const researchWs = useRef<WebSocket | null>(null);

  const addResearchLog = useCallback((log: LogEntry) => {
    setResearchState((prev) => ({ ...prev, logs: [...prev.logs, log] }));
  }, []);

  const startResearch = useCallback(
    (
      topic: string,
      kb: string,
      planMode: string = "medium",
      enabledTools: string[] = ["RAG"],
      skipRephrase: boolean = false,
    ) => {
      if (researchWs.current) researchWs.current.close();

      setResearchState((prev) => ({
        ...prev,
        status: "running",
        logs: [],
        report: null,
        topic,
        selectedKb: kb,
        progress: {
          stage: null,
          status: "",
          executionMode: undefined,
          totalBlocks: undefined,
          currentBlock: undefined,
          currentSubTopic: undefined,
          currentBlockId: undefined,
          iterations: undefined,
          maxIterations: undefined,
          toolsUsed: undefined,
          currentTool: undefined,
          currentQuery: undefined,
          currentRationale: undefined,
          queriesUsed: undefined,
          activeTasks: undefined,
          activeCount: undefined,
          completedCount: undefined,
          keptBlocks: undefined,
          sections: undefined,
          wordCount: undefined,
          citations: undefined,
        },
      }));

      const ws = new WebSocket(wsUrl("/api/v1/research/run"));
      researchWs.current = ws;

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            topic,
            kb_name: kb,
            plan_mode: planMode,
            enabled_tools: enabledTools,
            skip_rephrase: skipRephrase,
          }),
        );
        addResearchLog({
          type: "system",
          content: `Starting Research Pipeline (Plan: ${planMode}, Tools: ${enabledTools.join("+")}, Optimization: ${!skipRephrase ? "On" : "Off/Pre-done"})...`,
        });
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "log") {
          addResearchLog(data);
        } else if (data.type === "progress") {
          setResearchState((prev) => {
            // Parse active tasks for parallel mode
            const activeTasks: ActiveTaskInfo[] =
              data.active_tasks?.map((t: any) => ({
                block_id: t.block_id,
                sub_topic: t.sub_topic,
                status: t.status,
                iteration: t.iteration || 0,
                max_iterations: t.max_iterations,
                current_tool: t.current_tool,
                current_query: t.current_query,
                tools_used: t.tools_used,
              })) ?? prev.progress.activeTasks;

            // Parse queries used
            const queriesUsed: QueryInfo[] =
              data.queries_used?.map((q: any) => ({
                query: q.query,
                tool_type: q.tool_type,
                rationale: q.rationale,
                iteration: q.iteration,
              })) ?? prev.progress.queriesUsed;

            return {
              ...prev,
              progress: {
                stage: data.stage,
                status: data.status,
                executionMode:
                  data.execution_mode ?? prev.progress.executionMode,
                totalBlocks: data.total_blocks ?? prev.progress.totalBlocks,
                currentBlock: data.current_block ?? prev.progress.currentBlock,
                currentSubTopic:
                  data.sub_topic ?? prev.progress.currentSubTopic,
                currentBlockId: data.block_id ?? prev.progress.currentBlockId,
                iterations:
                  data.iteration ?? data.iterations ?? prev.progress.iterations,
                maxIterations:
                  data.max_iterations ?? prev.progress.maxIterations,
                toolsUsed: data.tools_used ?? prev.progress.toolsUsed,
                currentTool: data.tool_type ?? prev.progress.currentTool,
                currentQuery: data.query ?? prev.progress.currentQuery,
                currentRationale:
                  data.rationale ?? prev.progress.currentRationale,
                queriesUsed: queriesUsed,
                activeTasks: activeTasks,
                activeCount: data.active_count ?? prev.progress.activeCount,
                completedCount:
                  data.completed_count ?? prev.progress.completedCount,
                keptBlocks: data.kept_blocks ?? prev.progress.keptBlocks,
                sections: data.sections ?? prev.progress.sections,
                wordCount: data.word_count ?? prev.progress.wordCount,
                citations: data.citations ?? prev.progress.citations,
              },
            };
          });
        } else if (data.type === "result") {
          setResearchState((prev) => ({
            ...prev,
            status: "completed",
            report: data.report,
          }));
          ws.close();
        } else if (data.type === "error") {
          addResearchLog({
            type: "error",
            content: `Error: ${data.content || data.message || "Unknown error"}`,
          });
          setResearchState((prev) => ({ ...prev, status: "idle" }));
        }
      };

      ws.onerror = () => {
        addResearchLog({
          type: "error",
          content: "WebSocket connection error",
        });
        setResearchState((prev) => ({
          ...prev,
          status: "idle",
          progress: {
            stage: null,
            status: "",
            executionMode: undefined,
            activeTasks: undefined,
          },
        }));
      };

      ws.onclose = () => {
        if (researchWs.current === ws) {
          researchWs.current = null;
        }
      };
    },
    [addResearchLog],
  );

  return (
    <ResearchContext.Provider
      value={{
        researchState,
        setResearchState,
        startResearch,
      }}
    >
      {children}
    </ResearchContext.Provider>
  );
}

export const useResearch = () => {
  const context = useContext(ResearchContext);
  if (!context)
    throw new Error("useResearch must be used within ResearchProvider");
  return context;
};
