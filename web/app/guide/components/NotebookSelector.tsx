"use client";

import {
  BookOpen,
  Loader2,
  ChevronRight,
  ChevronDown,
  Sparkles,
  Check,
} from "lucide-react";
import {
  Notebook,
  NotebookRecord,
  SelectedRecord,
  getTypeColor,
} from "../types";

interface NotebookSelectorProps {
  notebooks: Notebook[];
  expandedNotebooks: Set<string>;
  notebookRecordsMap: Map<string, NotebookRecord[]>;
  selectedRecords: Map<string, SelectedRecord>;
  loadingNotebooks: boolean;
  loadingRecordsFor: Set<string>;
  isLoading: boolean;
  onToggleExpanded: (notebookId: string) => void;
  onToggleRecord: (
    record: NotebookRecord,
    notebookId: string,
    notebookName: string,
  ) => void;
  onSelectAll: (notebookId: string, notebookName: string) => void;
  onDeselectAll: (notebookId: string) => void;
  onClearAll: () => void;
  onCreateSession: () => void;
}

export default function NotebookSelector({
  notebooks,
  expandedNotebooks,
  notebookRecordsMap,
  selectedRecords,
  loadingNotebooks,
  loadingRecordsFor,
  isLoading,
  onToggleExpanded,
  onToggleRecord,
  onSelectAll,
  onDeselectAll,
  onClearAll,
  onCreateSession,
}: NotebookSelectorProps) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden">
      <div className="p-3 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex justify-between items-center">
        <h2 className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          Select Source (Cross-Notebook)
        </h2>
        {selectedRecords.size > 0 && (
          <button
            onClick={onClearAll}
            className="text-xs text-slate-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400"
          >
            Clear ({selectedRecords.size})
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto max-h-[400px]">
        {loadingNotebooks ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-indigo-600 dark:text-indigo-400" />
          </div>
        ) : notebooks.length === 0 ? (
          <div className="p-4 text-center text-sm text-slate-400 dark:text-slate-500">
            No notebooks with records found
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {notebooks.map((notebook) => {
              const isExpanded = expandedNotebooks.has(notebook.id);
              const records = notebookRecordsMap.get(notebook.id) || [];
              const isLoadingRecords = loadingRecordsFor.has(notebook.id);
              const selectedFromThis = records.filter((r) =>
                selectedRecords.has(r.id),
              ).length;

              return (
                <div key={notebook.id}>
                  {/* Notebook Header */}
                  <div
                    className="p-3 flex items-center gap-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                    onClick={() => onToggleExpanded(notebook.id)}
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-slate-400 dark:text-slate-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-slate-400 dark:text-slate-500" />
                    )}
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{
                        backgroundColor: notebook.color || "#94a3b8",
                      }}
                    />
                    <span className="flex-1 text-sm font-medium text-slate-700 dark:text-slate-200 truncate">
                      {notebook.name}
                    </span>
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      {selectedFromThis > 0 && (
                        <span className="text-indigo-600 dark:text-indigo-400 font-medium">
                          {selectedFromThis}/
                        </span>
                      )}
                      {notebook.record_count}
                    </span>
                  </div>

                  {/* Records List */}
                  {isExpanded && (
                    <div className="pl-6 pr-2 pb-2 bg-slate-50/50 dark:bg-slate-800/50">
                      {isLoadingRecords ? (
                        <div className="flex items-center justify-center py-4">
                          <Loader2 className="w-4 h-4 animate-spin text-indigo-600 dark:text-indigo-400" />
                        </div>
                      ) : records.length === 0 ? (
                        <div className="py-2 text-xs text-slate-400 dark:text-slate-500 text-center">
                          No records
                        </div>
                      ) : (
                        <>
                          <div className="flex gap-2 mb-2">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onSelectAll(notebook.id, notebook.name);
                              }}
                              className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
                            >
                              Select All
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                onDeselectAll(notebook.id);
                              }}
                              className="text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300"
                            >
                              Deselect
                            </button>
                          </div>
                          <div className="space-y-1">
                            {records.map((record) => (
                              <div
                                key={record.id}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onToggleRecord(
                                    record,
                                    notebook.id,
                                    notebook.name,
                                  );
                                }}
                                className={`p-2 rounded-lg cursor-pointer transition-all border ${
                                  selectedRecords.has(record.id)
                                    ? "bg-indigo-50 dark:bg-indigo-900/30 border-indigo-200 dark:border-indigo-700"
                                    : "hover:bg-white dark:hover:bg-slate-700 border-transparent hover:border-slate-200 dark:hover:border-slate-600"
                                }`}
                              >
                                <div className="flex items-center gap-2">
                                  <div
                                    className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${
                                      selectedRecords.has(record.id)
                                        ? "bg-indigo-500 border-indigo-500 text-white"
                                        : "border-slate-300 dark:border-slate-500"
                                    }`}
                                  >
                                    {selectedRecords.has(record.id) && (
                                      <Check className="w-2.5 h-2.5" />
                                    )}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <span
                                      className={`text-[10px] font-bold uppercase px-1 py-0.5 rounded ${getTypeColor(record.type)}`}
                                    >
                                      {record.type}
                                    </span>
                                    <span className="text-xs text-slate-700 dark:text-slate-200 ml-2 truncate">
                                      {record.title}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Generate Button */}
      <div className="p-3 border-t border-slate-100 dark:border-slate-700">
        <button
          onClick={onCreateSession}
          disabled={isLoading || selectedRecords.size === 0}
          className="w-full px-4 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-xl hover:from-indigo-600 hover:to-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium shadow-md shadow-indigo-500/20"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Generate Learning Plan ({selectedRecords.size} items)
            </>
          )}
        </button>
      </div>
    </div>
  );
}
