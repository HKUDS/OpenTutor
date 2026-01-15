import React from "react";
import {
  X,
  Activity,
  CheckCircle2,
  Loader2,
  Target,
  Search,
  Database,
  Sparkles,
  RefreshCw,
  FileText,
  Clock,
  Trash2,
} from "lucide-react";

interface LogEntry {
  type: string;
  content: string;
  timestamp?: number;
  level?: string;
}

interface SubFocus {
  id: string;
  focus: string;
  scenario_hint?: string;
}

interface LogDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  logs: LogEntry[];
  stage: string | null;
  progress?: {
    current?: number;
    total?: number;
    status?: string;
  };
  subFocuses?: SubFocus[];
  mode?: "custom" | "mimic";
  topic?: string;
  difficulty?: string;
  questionType?: string;
  count?: number;
  onClearLogs?: () => void;
}

export const LogDrawer: React.FC<LogDrawerProps> = ({
  isOpen,
  onClose,
  logs,
  stage,
  progress,
  subFocuses = [],
  mode = "custom",
  topic,
  difficulty,
  questionType,
  count,
  onClearLogs,
}) => {
  const isMimicMode = mode === "mimic";
  const isIdle = stage === "idle" || stage === null;
  const isGenerating = stage === "generating" || stage === "validating";
  const isComplete = stage === "complete";

  // Custom mode steps
  const customModeSteps = [
    {
      id: "init",
      label: "Initializing",
      icon: Sparkles,
      active: stage === "planning" && !progress?.status,
      done:
        stage === "researching" ||
        progress?.status === "generating_queries" ||
        progress?.status === "retrieving" ||
        progress?.status === "creating_plan" ||
        progress?.status === "plan_ready" ||
        isGenerating ||
        isComplete,
    },
    {
      id: "query",
      label: "Generating Search Queries",
      icon: Search,
      active:
        progress?.status === "generating_queries" ||
        progress?.status === "splitting_queries",
      done:
        stage === "researching" ||
        progress?.status === "retrieving" ||
        progress?.status === "creating_plan" ||
        progress?.status === "plan_ready" ||
        isGenerating ||
        isComplete,
    },
    {
      id: "research",
      label: "Retrieving Knowledge",
      icon: Database,
      active: stage === "researching" || progress?.status === "retrieving",
      done:
        progress?.status === "creating_plan" ||
        progress?.status === "plan_ready" ||
        isGenerating ||
        isComplete,
    },
    {
      id: "plan",
      label: "Creating Question Plan",
      icon: Target,
      active:
        progress?.status === "creating_plan" ||
        progress?.status === "planning_focuses",
      done: progress?.status === "plan_ready" || isGenerating || isComplete,
    },
  ];

  // Mimic mode steps
  const mimicModeSteps = [
    {
      id: "upload",
      label: "Uploading PDF",
      icon: Sparkles,
      active: stage === "uploading",
      done:
        stage === "parsing" ||
        stage === "extracting" ||
        isGenerating ||
        isComplete,
    },
    {
      id: "parse",
      label: "Parsing PDF (MinerU)",
      icon: RefreshCw,
      active: stage === "parsing",
      done: stage === "extracting" || isGenerating || isComplete,
    },
    {
      id: "extract",
      label: "Extracting Questions",
      icon: Search,
      active: stage === "extracting",
      done: isGenerating || isComplete,
    },
    {
      id: "ready",
      label: "Ready to Generate",
      icon: Target,
      active: false,
      done: isGenerating || isComplete,
    },
  ];

  const planningSteps = isMimicMode ? mimicModeSteps : customModeSteps;

  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/30 dark:bg-black/50 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Drawer - matches the app styling */}
      <div
        className={`
          fixed top-0 right-0 h-full w-full sm:w-[400px] bg-white dark:bg-slate-800
          border-l border-slate-200 dark:border-slate-700 z-50
          transform transition-transform duration-300 ease-out
          shadow-2xl
          ${isOpen ? "translate-x-0" : "translate-x-full"}
          flex flex-col
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 shrink-0">
          <div className="flex items-center gap-3">
            <div
              className={`p-2 rounded-lg ${
                isComplete
                  ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400"
                  : isIdle
                    ? "bg-slate-100 dark:bg-slate-700 text-slate-400"
                    : "bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400"
              }`}
            >
              {isComplete ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : isIdle ? (
                <Clock className="w-4 h-4" />
              ) : (
                <Activity className="w-4 h-4" />
              )}
            </div>
            <div>
              <h2 className="font-semibold text-slate-700 dark:text-slate-200 text-sm">
                {isComplete
                  ? "Generation Complete"
                  : isIdle
                    ? "Ready"
                    : "Generating"}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {stage || "idle"}
                {progress?.current && progress?.total
                  ? ` · ${progress.current}/${progress.total}`
                  : ""}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto bg-slate-50/30 dark:bg-slate-900/30">
          {/* Topic Info */}
          {!isMimicMode && topic && (
            <div className="px-4 py-4 border-b border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800">
              <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                Configuration
              </p>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200 mb-2">
                {topic}
              </p>
              <div className="flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400">
                <span>
                  Difficulty:{" "}
                  <strong className="capitalize text-slate-700 dark:text-slate-200">
                    {difficulty}
                  </strong>
                </span>
                <span>
                  Type:{" "}
                  <strong className="capitalize text-slate-700 dark:text-slate-200">
                    {questionType}
                  </strong>
                </span>
                <span>
                  Count:{" "}
                  <strong className="text-slate-700 dark:text-slate-200">
                    {count}
                  </strong>
                </span>
              </div>
            </div>
          )}

          {/* Mimic Mode Info */}
          {isMimicMode && (
            <div className="px-4 py-4 border-b border-slate-100 dark:border-slate-700 bg-amber-50 dark:bg-amber-900/20">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <p className="text-xs font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wider">
                  Mimic Exam Mode
                </p>
              </div>
              <p className="text-sm text-amber-800 dark:text-amber-300">
                Generating questions based on reference exam paper
              </p>
            </div>
          )}

          {/* Planning Steps Timeline */}
          {!isIdle && (
            <div className="px-4 py-4 border-b border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800">
              <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-4">
                Progress
              </p>
              <div className="space-y-3">
                {planningSteps.map((step) => (
                  <div key={step.id} className="flex items-center gap-3">
                    <div
                      className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
                        step.done
                          ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400"
                          : step.active
                            ? "bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400"
                            : "bg-slate-100 dark:bg-slate-700 text-slate-400 dark:text-slate-500"
                      }`}
                    >
                      {step.done ? (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                      ) : step.active ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <step.icon className="w-3.5 h-3.5" />
                      )}
                    </div>
                    <span
                      className={`text-sm ${
                        step.done
                          ? "text-emerald-700 dark:text-emerald-300"
                          : step.active
                            ? "text-purple-700 dark:text-purple-300 font-medium"
                            : "text-slate-400 dark:text-slate-500"
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sub-Focuses */}
          {subFocuses.length > 0 && (
            <div className="px-4 py-4 border-b border-slate-100 dark:border-slate-700 bg-white dark:bg-slate-800">
              <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                Question Focuses ({subFocuses.length})
              </p>
              <div className="space-y-2 max-h-[200px] overflow-y-auto">
                {subFocuses.map((focus) => (
                  <div
                    key={focus.id}
                    className="px-3 py-2 bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs rounded-lg border border-slate-100 dark:border-slate-600"
                  >
                    <div className="flex items-center gap-2 font-semibold text-purple-600 dark:text-purple-400 mb-1">
                      <Target className="w-3 h-3" />
                      {focus.id}
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 line-clamp-2">
                      {focus.focus}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Live Logs */}
          <div className="px-4 py-4 bg-white dark:bg-slate-800">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Logs ({logs.length})
              </p>
              {logs.length > 0 && onClearLogs && (
                <button
                  onClick={onClearLogs}
                  className="flex items-center gap-1 text-xs text-slate-400 hover:text-red-500 dark:hover:text-red-400 px-2 py-1 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                  title="Clear logs"
                >
                  <Trash2 className="w-3 h-3" />
                  Clear
                </button>
              )}
            </div>
            {logs.length === 0 ? (
              <div className="text-center py-8 text-slate-400 dark:text-slate-500">
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-30" />
                <p className="text-xs">Waiting for logs...</p>
              </div>
            ) : (
              <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
                {logs.slice(-50).map((log, idx) => (
                  <div
                    key={idx}
                    className={`text-xs px-3 py-2 rounded-lg break-words ${
                      log.type === "error"
                        ? "bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 border border-red-100 dark:border-red-800"
                        : log.type === "success"
                          ? "bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 border border-emerald-100 dark:border-emerald-800"
                          : "bg-slate-50 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-100 dark:border-slate-600"
                    }`}
                  >
                    {log.content}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};
