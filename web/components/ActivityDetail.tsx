import { useState } from "react";
import { X, FileText, HelpCircle, Search, Clock, Database } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { processLatexContent } from "@/lib/latex";

interface ActivityDetailProps {
  activity: any;
  onClose: () => void;
}

export default function ActivityDetail({
  activity,
  onClose,
}: ActivityDetailProps) {
  if (!activity) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[150vh] flex flex-col animate-in zoom-in-95 duration-300">
        {/* Header */}
        <div className="p-6 border-b border-slate-100 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                activity.type === "solve"
                  ? "bg-blue-50 text-blue-600"
                  : activity.type === "question"
                    ? "bg-purple-50 text-purple-600"
                    : "bg-emerald-50 text-emerald-600"
              }`}
            >
              {activity.type === "solve" && <HelpCircle className="w-5 h-5" />}
              {activity.type === "question" && <FileText className="w-5 h-5" />}
              {activity.type === "research" && <Search className="w-5 h-5" />}
            </div>
            <div>
              <h2 className="font-bold text-slate-900 text-lg">
                Activity Details
              </h2>
              <p className="text-xs text-slate-500 flex items-center gap-2">
                <Clock className="w-3 h-3" />
                {new Date(activity.timestamp * 1000).toLocaleString()}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Meta Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
              <div className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-1">
                Type
              </div>
              <div className="font-medium text-slate-900 capitalize">
                {activity.type}
              </div>
            </div>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
              <div className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-1">
                Knowledge Base
              </div>
              <div className="font-medium text-slate-900 flex items-center gap-2">
                <Database className="w-4 h-4 text-slate-400" />
                {activity.content?.kb_name || "Unknown"}
              </div>
            </div>
          </div>

          {/* Activity Specific Content */}

          {/* 1. SOLVE */}
          {activity.type === "solve" && (
            <>
              <div className="space-y-2">
                <h3 className="font-bold text-slate-900">Question</h3>
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-slate-800 leading-relaxed">
                  {activity.content.question}
                </div>
              </div>
              <div className="space-y-2">
                <h3 className="font-bold text-slate-900">Final Answer</h3>
                <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm">
                  <div className="prose prose-slate dark:prose-invert max-w-none prose-sm">
                    <ReactMarkdown
                      remarkPlugins={[remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                    >
                      {processLatexContent(activity.content.answer)}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* 2. QUESTION */}
          {activity.type === "question" && (
            <>
              <div className="space-y-2">
                <h3 className="font-bold text-slate-900">Parameters</h3>
                <div className="grid grid-cols-3 gap-3">
                  <div className="px-3 py-2 border rounded-lg text-sm text-slate-600">
                    <span className="font-bold">Topic:</span>{" "}
                    {activity.content?.requirement?.knowledge_point || "N/A"}
                  </div>
                  <div className="px-3 py-2 border rounded-lg text-sm text-slate-600">
                    <span className="font-bold">Difficulty:</span>{" "}
                    {activity.content?.requirement?.difficulty || "N/A"}
                  </div>
                  <div className="px-3 py-2 border rounded-lg text-sm text-slate-600">
                    <span className="font-bold">Type:</span>{" "}
                    {activity.content?.requirement?.question_type ||
                      activity.content?.question?.question_type ||
                      "N/A"}
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-bold text-slate-900">Generated Question</h3>
                <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm space-y-4">
                  <p className="text-lg font-medium text-slate-900">
                    {activity.content?.question?.content ||
                      activity.content?.question?.question ||
                      "No question content"}
                  </p>

                  {/* Handle options as object (A, B, C, D format) or array */}
                  {activity.content?.question?.options && (
                    <div className="space-y-2">
                      {Array.isArray(activity.content.question.options)
                        ? // Array format
                          activity.content.question.options.map(
                            (opt: string, i: number) => (
                              <div
                                key={i}
                                className="p-3 border border-slate-100 rounded-lg bg-slate-50 text-sm"
                              >
                                <span className="font-bold text-purple-600 mr-2">
                                  {String.fromCharCode(65 + i)}.
                                </span>
                                {opt}
                              </div>
                            ),
                          )
                        : // Object format { "A": "...", "B": "..." }
                          Object.entries(activity.content.question.options).map(
                            ([key, value]) => (
                              <div
                                key={key}
                                className="p-3 border border-slate-100 rounded-lg bg-slate-50 text-sm"
                              >
                                <span className="font-bold text-purple-600 mr-2">
                                  {key}.
                                </span>
                                {value as string}
                              </div>
                            ),
                          )}
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <h3 className="font-bold text-slate-900 text-green-700">
                  Correct Answer & Explanation
                </h3>
                <div className="p-4 bg-green-50 rounded-xl border border-green-100 text-green-800 space-y-2">
                  <p className="font-bold">
                    Answer:{" "}
                    {activity.content?.question?.answer ||
                      activity.content?.question?.correct_answer ||
                      "N/A"}
                  </p>
                  <p className="text-sm leading-relaxed">
                    {activity.content?.question?.explanation ||
                      "No explanation provided"}
                  </p>
                </div>
              </div>
            </>
          )}

          {/* 3. RESEARCH */}
          {activity.type === "research" && (
            <>
              <div className="space-y-2">
                <h3 className="font-bold text-slate-900">Topic</h3>
                <div className="text-lg font-medium text-slate-800">
                  {activity.content.topic}
                </div>
              </div>
              <div className="space-y-2">
                <h3 className="font-bold text-slate-900">Report Preview</h3>
                <div className="p-6 bg-white rounded-xl border border-slate-200 shadow-sm max-h-96 overflow-y-auto font-mono text-xs text-slate-600">
                  {activity.content.report}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-100 bg-slate-50 rounded-b-2xl flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2.5 bg-slate-900 text-white rounded-xl font-medium hover:bg-slate-800 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
