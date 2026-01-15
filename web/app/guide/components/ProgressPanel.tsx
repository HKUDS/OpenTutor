"use client";

import { Loader2, Play, ChevronRight, CheckCircle2 } from "lucide-react";
import { SessionState } from "../types";

interface ProgressPanelProps {
  sessionState: SessionState;
  isLoading: boolean;
  canStart: boolean;
  canNext: boolean;
  isLastKnowledge: boolean;
  onStartLearning: () => void;
  onNextKnowledge: () => void;
}

export default function ProgressPanel({
  sessionState,
  isLoading,
  canStart,
  canNext,
  isLastKnowledge,
  onStartLearning,
  onNextKnowledge,
}: ProgressPanelProps) {
  return (
    <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          Learning Progress
        </span>
        <span className="text-xs text-slate-400 dark:text-slate-500">
          {sessionState.progress}%
        </span>
      </div>
      <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden mb-4">
        <div
          className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500"
          style={{ width: `${sessionState.progress}%` }}
        />
      </div>
      {sessionState.knowledge_points.length > 0 && (
        <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
          Knowledge Point {sessionState.current_index + 1} /{" "}
          {sessionState.knowledge_points.length}
        </p>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2">
        {canStart && (
          <button
            onClick={onStartLearning}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm font-medium"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Start Learning
              </>
            )}
          </button>
        )}

        {canNext && (
          <button
            onClick={onNextKnowledge}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm font-medium"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading...
              </>
            ) : (
              <>
                <ChevronRight className="w-4 h-4" />
                Next
              </>
            )}
          </button>
        )}

        {isLastKnowledge && (
          <button
            onClick={onNextKnowledge}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm font-medium"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating Summary...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Complete Learning
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
