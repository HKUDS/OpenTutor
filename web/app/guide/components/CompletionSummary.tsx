"use client";

import { CheckCircle2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { processLatexContent } from "@/lib/latex";

interface CompletionSummaryProps {
  summary: string;
}

export default function CompletionSummary({ summary }: CompletionSummaryProps) {
  // Table components for ReactMarkdown
  const tableComponents = {
    table: ({ node, ...props }: any) => (
      <div className="overflow-x-auto my-6 rounded-lg border border-slate-200 shadow-sm">
        <table
          className="min-w-full divide-y divide-slate-200 text-sm"
          {...props}
        />
      </div>
    ),
    thead: ({ node, ...props }: any) => (
      <thead className="bg-slate-50" {...props} />
    ),
    th: ({ node, ...props }: any) => (
      <th
        className="px-4 py-3 text-left font-semibold text-slate-700 whitespace-nowrap border-b border-slate-200"
        {...props}
      />
    ),
    tbody: ({ node, ...props }: any) => (
      <tbody className="divide-y divide-slate-100 bg-white" {...props} />
    ),
    td: ({ node, ...props }: any) => (
      <td
        className="px-4 py-3 text-slate-600 border-b border-slate-100"
        {...props}
      />
    ),
    tr: ({ node, ...props }: any) => (
      <tr className="hover:bg-slate-50/50 transition-colors" {...props} />
    ),
  };

  return (
    <div className="flex-1 bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden relative">
      {/* Summary Header */}
      <div className="p-4 border-b border-slate-100 dark:border-slate-700 bg-gradient-to-r from-emerald-50 to-indigo-50 dark:from-emerald-900/20 dark:to-indigo-900/20 flex items-center justify-between shrink-0">
        <h2 className="font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          Learning Summary
        </h2>
      </div>
      {/* Summary Content */}
      <div className="flex-1 overflow-y-auto p-8 bg-white dark:bg-slate-800">
        <div className="prose prose-slate dark:prose-invert prose-headings:font-bold prose-h1:text-2xl prose-h2:text-xl max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
            components={tableComponents}
          >
            {processLatexContent(summary || "")}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
