"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { processLatexContent } from "@/lib/latex";

interface MarkdownRendererProps {
  content: string;
  className?: string;
  variant?: "default" | "compact" | "prose";
}

/**
 * Shared MarkdownRenderer component with KaTeX support and consistent table styling
 */
export default function MarkdownRenderer({
  content,
  className = "",
  variant = "default",
}: MarkdownRendererProps) {
  // Table components with consistent styling
  const tableComponents = {
    table: ({ node, ...props }: any) => (
      <div
        className={`overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm ${
          variant === "compact" ? "my-2" : "my-4"
        }`}
      >
        <table
          className="min-w-full divide-y divide-slate-200 dark:divide-slate-700 text-sm"
          {...props}
        />
      </div>
    ),
    thead: ({ node, ...props }: any) => (
      <thead className="bg-slate-50 dark:bg-slate-800" {...props} />
    ),
    th: ({ node, ...props }: any) => (
      <th
        className={`text-left font-semibold text-slate-700 dark:text-slate-300 whitespace-nowrap border-b border-slate-200 dark:border-slate-700 ${
          variant === "compact" ? "px-2 py-1.5" : "px-3 py-2"
        }`}
        {...props}
      />
    ),
    tbody: ({ node, ...props }: any) => (
      <tbody
        className="divide-y divide-slate-100 dark:divide-slate-700 bg-white dark:bg-slate-900"
        {...props}
      />
    ),
    td: ({ node, ...props }: any) => (
      <td
        className={`text-slate-600 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700 ${
          variant === "compact" ? "px-2 py-1.5" : "px-3 py-2"
        }`}
        {...props}
      />
    ),
    tr: ({ node, ...props }: any) => (
      <tr
        className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50 transition-colors"
        {...props}
      />
    ),
  };

  // Code block styling
  const codeComponents = {
    code: ({
      node,
      inline,
      className: codeClassName,
      children,
      ...props
    }: any) => {
      if (inline) {
        return (
          <code
            className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded text-sm font-mono"
            {...props}
          >
            {children}
          </code>
        );
      }
      return (
        <code
          className={`block p-3 bg-slate-900 dark:bg-slate-950 text-slate-100 rounded-lg overflow-x-auto text-sm font-mono ${codeClassName || ""}`}
          {...props}
        >
          {children}
        </code>
      );
    },
    pre: ({ node, children, ...props }: any) => (
      <pre className="my-4" {...props}>
        {children}
      </pre>
    ),
  };

  const proseClasses =
    variant === "prose"
      ? "prose prose-slate dark:prose-invert prose-headings:font-bold prose-h1:text-2xl prose-h2:text-xl max-w-none"
      : "prose prose-sm max-w-none";

  return (
    <div className={`${proseClasses} ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          ...tableComponents,
          ...codeComponents,
        }}
      >
        {processLatexContent(content)}
      </ReactMarkdown>
    </div>
  );
}
