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
  QuestionContextState,
  QuestionProgressInfo,
  INITIAL_QUESTION_CONTEXT_STATE,
  DEFAULT_QUESTION_AGENT_STATUS,
  DEFAULT_QUESTION_TOKEN_STATS,
} from "@/types/question";
import { LogEntry } from "@/types/common";

// Context type
interface QuestionContextType {
  questionState: QuestionContextState;
  setQuestionState: React.Dispatch<React.SetStateAction<QuestionContextState>>;
  startQuestionGen: (
    topic: string,
    diff: string,
    type: string,
    count: number,
    kb: string,
  ) => void;
  startMimicQuestionGen: (
    file: File | null,
    paperPath: string,
    kb: string,
    maxQuestions?: number,
  ) => void;
  resetQuestionGen: () => void;
}

const QuestionContext = createContext<QuestionContextType | undefined>(
  undefined,
);

export function QuestionProvider({ children }: { children: React.ReactNode }) {
  const [questionState, setQuestionState] = useState<QuestionContextState>(
    INITIAL_QUESTION_CONTEXT_STATE,
  );
  const questionWs = useRef<WebSocket | null>(null);

  const addQuestionLog = useCallback((log: LogEntry) => {
    setQuestionState((prev) => ({ ...prev, logs: [...prev.logs, log] }));
  }, []);

  // Helper function to handle mimic WebSocket messages
  const handleMimicWsMessage = useCallback(
    (data: any, ws: WebSocket) => {
      const stageMap: Record<string, string> = {
        init: "uploading",
        upload: "uploading",
        parsing: "parsing",
        processing: "extracting",
      };

      switch (data.type) {
        case "log":
          addQuestionLog(data);
          break;

        case "status": {
          const mappedStage = stageMap[data.stage] || data.stage;
          addQuestionLog({
            type: "system",
            content: data.content || data.message || `Stage: ${data.stage}`,
          });
          if (mappedStage) {
            setQuestionState((prev) => ({
              ...prev,
              progress: { ...prev.progress, stage: mappedStage },
            }));
          }
          break;
        }

        case "progress": {
          const stage = data.stage || "generating";
          if (data.message) {
            addQuestionLog({ type: "system", content: data.message });
          }
          setQuestionState((prev) => ({
            ...prev,
            progress: {
              ...prev.progress,
              stage: stage,
              progress: {
                ...prev.progress.progress,
                current: data.current ?? prev.progress.progress.current,
                total:
                  data.total_questions ??
                  data.total ??
                  prev.progress.progress.total,
                status: data.status,
              },
            },
          }));
          if (
            stage === "extracting" &&
            data.status === "complete" &&
            data.reference_questions
          ) {
            setQuestionState((prev) => ({
              ...prev,
              progress: {
                ...prev.progress,
                progress: {
                  ...prev.progress.progress,
                  total:
                    data.total_questions || data.reference_questions.length,
                },
              },
            }));
          }
          break;
        }

        case "question_update": {
          const statusMessage =
            data.status === "generating"
              ? `Generating mimic question ${data.index}...`
              : data.status === "failed"
                ? `Question ${data.index} failed: ${data.error}`
                : `Question ${data.index}: ${data.status}`;
          addQuestionLog({
            type: data.status === "failed" ? "warning" : "system",
            content: statusMessage,
          });
          if (data.current !== undefined) {
            setQuestionState((prev) => ({
              ...prev,
              progress: {
                ...prev.progress,
                progress: { ...prev.progress.progress, current: data.current },
              },
            }));
          }
          break;
        }

        case "result": {
          const isExtended =
            data.extended || data.validation?.decision === "extended";
          addQuestionLog({
            type: "success",
            content: `✅ Question ${data.index || (data.current ?? 0)} generated successfully`,
          });
          setQuestionState((prev) => ({
            ...prev,
            results: [
              ...prev.results,
              {
                success: true,
                question_id: data.question_id || `q_${prev.results.length + 1}`,
                question: data.question,
                validation: data.validation,
                rounds: data.rounds || 1,
                reference_question: data.reference_question,
                extended: isExtended,
              },
            ],
            progress: {
              ...prev.progress,
              stage: "generating",
              progress: {
                ...prev.progress.progress,
                current: data.current ?? prev.results.length + 1,
                total: data.total ?? prev.progress.progress.total ?? 1,
              },
              extendedQuestions:
                (prev.progress.extendedQuestions || 0) + (isExtended ? 1 : 0),
            },
          }));
          break;
        }

        case "summary":
          addQuestionLog({
            type: "success",
            content: `Generation complete: ${data.successful}/${data.total_reference} succeeded`,
          });
          setQuestionState((prev) => ({
            ...prev,
            progress: {
              ...prev.progress,
              stage: "generating",
              progress: {
                current: data.successful,
                total: data.total_reference,
              },
              completedQuestions: data.successful,
              failedQuestions: data.failed,
            },
          }));
          break;

        case "complete":
          addQuestionLog({
            type: "success",
            content: "✅ Mimic generation completed!",
          });
          setQuestionState((prev) => ({
            ...prev,
            step: "result",
            progress: {
              ...prev.progress,
              stage: "complete",
              completedQuestions: prev.results.length,
            },
          }));
          ws.close();
          break;

        case "error":
          addQuestionLog({
            type: "error",
            content: `Error: ${data.content || data.message || "Unknown error"}`,
          });
          setQuestionState((prev) => ({
            ...prev,
            step: "config",
            progress: { stage: null, progress: {} },
          }));
          break;
      }
    },
    [addQuestionLog],
  );

  const startQuestionGen = useCallback(
    (topic: string, diff: string, type: string, count: number, kb: string) => {
      if (questionWs.current) questionWs.current.close();

      setQuestionState((prev) => ({
        ...prev,
        step: "generating",
        mode: "knowledge",
        logs: [],
        results: [],
        topic,
        difficulty: diff,
        type,
        count,
        selectedKb: kb,
        progress: {
          stage: count > 1 ? "planning" : "generating",
          progress: { current: 0, total: count },
          subFocuses: [],
          activeQuestions: [],
          completedQuestions: 0,
          failedQuestions: 0,
        },
        agentStatus: { ...DEFAULT_QUESTION_AGENT_STATUS },
        tokenStats: { ...DEFAULT_QUESTION_TOKEN_STATS },
      }));

      const ws = new WebSocket(wsUrl("/api/v1/question/generate"));
      questionWs.current = ws;

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            requirement: {
              knowledge_point: topic,
              difficulty: diff,
              question_type: type,
              additional_requirements: "Ensure clarity and academic rigor.",
            },
            count: count,
            kb_name: kb,
          }),
        );
        addQuestionLog({
          type: "system",
          content: "Initializing Generator...",
        });
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "log") {
          addQuestionLog(data);
          // Parse progress info from log content
          if (data.content.includes("Generating question")) {
            const match = data.content.match(/(\d+)\/(\d+)/);
            if (match) {
              setQuestionState((prev) => ({
                ...prev,
                progress: {
                  ...prev.progress,
                  stage: "generating",
                  progress: {
                    current: parseInt(match[1]),
                    total: parseInt(match[2]),
                  },
                },
              }));
            }
          }
          if (
            data.content.includes("Round") ||
            data.content.includes("round")
          ) {
            const match = data.content.match(/Round\s+(\d+)/i);
            if (match) {
              setQuestionState((prev) => ({
                ...prev,
                progress: {
                  ...prev.progress,
                  progress: {
                    ...prev.progress.progress,
                    round: parseInt(match[1]),
                  },
                },
              }));
            }
          }
          if (
            data.content.includes("Validation") ||
            data.content.includes("validation")
          ) {
            setQuestionState((prev) => ({
              ...prev,
              progress: {
                ...prev.progress,
                stage: "validating",
              },
            }));
          }
        } else if (data.type === "agent_status") {
          setQuestionState((prev) => ({
            ...prev,
            agentStatus: data.all_agents || {
              ...prev.agentStatus,
              [data.agent]: data.status,
            },
          }));
        } else if (data.type === "token_stats") {
          setQuestionState((prev) => ({
            ...prev,
            tokenStats: data.stats || prev.tokenStats,
          }));
        } else if (data.type === "progress") {
          setQuestionState((prev) => ({
            ...prev,
            progress: {
              stage: data.stage || prev.progress.stage,
              progress: {
                ...prev.progress.progress,
                ...data.progress,
                total: data.total ?? prev.progress.progress.total,
              },
              subFocuses:
                data.focuses || data.sub_focuses || prev.progress.subFocuses,
              activeQuestions: prev.progress.activeQuestions,
              completedQuestions:
                data.completed ?? prev.progress.completedQuestions,
              failedQuestions: data.failed ?? prev.progress.failedQuestions,
            },
          }));
        } else if (data.type === "question_update") {
          const statusLabel =
            data.status === "analyzing"
              ? "Analyzing relevance"
              : data.status === "generating"
                ? "Generating"
                : data.status === "done"
                  ? "Completed"
                  : data.status;
          addQuestionLog({
            type: data.status === "done" ? "success" : "system",
            content: `[${data.question_id}] ${statusLabel}${data.focus ? `: ${data.focus.slice(0, 50)}...` : ""}`,
          });
        } else if (data.type === "question_error") {
          addQuestionLog({
            type: "error",
            content: `[${data.question_id}] Error: ${data.error}${data.reason ? ` - ${data.reason}` : ""}`,
          });
        } else if (data.type === "knowledge_saved") {
          addQuestionLog({
            type: "success",
            content: `Background knowledge retrieved (${data.queries?.length || 0} queries)`,
          });
        } else if (data.type === "plan_ready") {
          const focuses = data.focuses || data.plan?.focuses || [];
          setQuestionState((prev) => ({
            ...prev,
            progress: {
              ...prev.progress,
              stage: "planning",
              subFocuses: focuses,
              progress: {
                ...prev.progress.progress,
                status: "plan_ready",
              },
            },
          }));
          addQuestionLog({
            type: "success",
            content: `Question plan created with ${focuses.length} focuses`,
          });
        } else if (data.type === "batch_summary") {
          setQuestionState((prev) => ({
            ...prev,
            progress: {
              ...prev.progress,
              subFocuses:
                data.sub_focuses ||
                data.plan?.focuses ||
                prev.progress.subFocuses,
              completedQuestions: data.completed || prev.results.length,
              failedQuestions: data.failed || 0,
              progress: {
                ...prev.progress.progress,
                current: data.completed || prev.results.length,
                total: data.requested || prev.count,
              },
            },
          }));
          addQuestionLog({
            type: "success",
            content: `Generation complete: ${data.completed}/${data.requested} questions generated${data.failed > 0 ? `, ${data.failed} failed` : ""}`,
          });
        } else if (data.type === "result") {
          const isExtended =
            data.extended || data.validation?.decision === "extended";
          const questionPreview =
            data.question?.question?.slice(0, 50) || "Unknown";
          addQuestionLog({
            type: "success",
            content: `Question ${data.question_id || (data.index !== undefined ? `#${data.index + 1}` : "")} generated: ${questionPreview}...`,
          });
          setQuestionState((prev) => ({
            ...prev,
            results: [
              ...prev.results,
              {
                success: true,
                question_id: data.question_id || `q_${prev.results.length + 1}`,
                question: data.question,
                validation: data.validation,
                rounds: data.rounds || 1,
                extended: isExtended,
              },
            ],
            progress: {
              ...prev.progress,
              stage: "generating",
              completedQuestions: prev.results.length + 1,
              progress: {
                ...prev.progress.progress,
                current: prev.results.length + 1,
                total: prev.count,
                round: data.rounds || 1,
              },
              extendedQuestions:
                (prev.progress.extendedQuestions || 0) + (isExtended ? 1 : 0),
            },
          }));
        } else if (data.type === "complete") {
          setQuestionState((prev) => ({
            ...prev,
            step: "result",
            progress: {
              ...prev.progress,
              stage: "complete",
              completedQuestions: prev.results.length,
            },
          }));
          ws.close();
        } else if (data.type === "error") {
          addQuestionLog({
            type: "error",
            content: `Error: ${data.content || data.message || "Unknown error"}`,
          });
          setQuestionState((prev) => ({
            ...prev,
            progress: {
              stage: null,
              progress: {},
            },
          }));
        }
      };

      ws.onerror = () => {
        addQuestionLog({
          type: "error",
          content: "WebSocket connection error",
        });
        setQuestionState((prev) => ({
          ...prev,
          step: "config",
          progress: {
            stage: null,
            progress: {},
          },
          agentStatus: { ...DEFAULT_QUESTION_AGENT_STATUS },
        }));
      };

      ws.onclose = () => {
        if (questionWs.current === ws) {
          questionWs.current = null;
        }
      };
    },
    [addQuestionLog],
  );

  const startMimicQuestionGen = useCallback(
    async (
      file: File | null,
      paperPath: string,
      kb: string,
      maxQuestions?: number,
    ) => {
      if (questionWs.current) questionWs.current.close();

      const hasFile = file !== null;
      const hasParsedPath = paperPath && paperPath.trim() !== "";

      if (!hasFile && !hasParsedPath) {
        addQuestionLog({
          type: "error",
          content:
            "Please upload a PDF file or provide a parsed exam directory",
        });
        return;
      }

      setQuestionState((prev) => ({
        ...prev,
        step: "generating",
        mode: "mimic",
        logs: [],
        results: [],
        selectedKb: kb,
        uploadedFile: file,
        paperPath: paperPath,
        progress: {
          stage: hasFile ? "uploading" : "parsing",
          progress: { current: 0, total: maxQuestions || 1 },
        },
        agentStatus: { ...DEFAULT_QUESTION_AGENT_STATUS },
        tokenStats: { ...DEFAULT_QUESTION_TOKEN_STATS },
      }));

      const ws = new WebSocket(wsUrl("/api/v1/question/mimic"));
      questionWs.current = ws;

      ws.onopen = async () => {
        if (hasFile && file) {
          addQuestionLog({
            type: "system",
            content: "Preparing to upload PDF file...",
          });
          const reader = new FileReader();
          reader.onload = () => {
            const base64Data = (reader.result as string).split(",")[1];
            ws.send(
              JSON.stringify({
                mode: "upload",
                pdf_data: base64Data,
                pdf_name: file.name,
                kb_name: kb,
                max_questions: maxQuestions,
              }),
            );
            addQuestionLog({
              type: "system",
              content: `Uploaded: ${file.name}, parsing...`,
            });
          };
          reader.readAsDataURL(file);
        } else {
          ws.send(
            JSON.stringify({
              mode: "parsed",
              paper_path: paperPath,
              kb_name: kb,
              max_questions: maxQuestions,
            }),
          );
          addQuestionLog({
            type: "system",
            content: "Initializing Mimic Generator...",
          });
        }
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMimicWsMessage(data, ws);
      };

      ws.onerror = () => {
        addQuestionLog({
          type: "error",
          content: "WebSocket connection error",
        });
        setQuestionState((prev) => ({ ...prev, step: "config" }));
      };
    },
    [addQuestionLog, handleMimicWsMessage],
  );

  const resetQuestionGen = useCallback(() => {
    setQuestionState((prev) => ({
      ...prev,
      step: "config",
      results: [],
      logs: [],
      progress: {
        stage: null,
        progress: {},
        subFocuses: [],
        activeQuestions: [],
        completedQuestions: 0,
        failedQuestions: 0,
      },
      agentStatus: { ...DEFAULT_QUESTION_AGENT_STATUS },
      tokenStats: { ...DEFAULT_QUESTION_TOKEN_STATS },
      uploadedFile: null,
      paperPath: "",
    }));
  }, []);

  return (
    <QuestionContext.Provider
      value={{
        questionState,
        setQuestionState,
        startQuestionGen,
        startMimicQuestionGen,
        resetQuestionGen,
      }}
    >
      {children}
    </QuestionContext.Provider>
  );
}

export const useQuestion = () => {
  const context = useContext(QuestionContext);
  if (!context)
    throw new Error("useQuestion must be used within QuestionProvider");
  return context;
};
