"use client";

import { useRef, useEffect } from "react";
import { Bug, Loader2 } from "lucide-react";
import { useKaTeXInjection } from "../hooks";

interface HTMLViewerProps {
  html: string;
  currentIndex: number;
  loadingMessage: string;
  onOpenDebugModal: () => void;
}

export default function HTMLViewer({
  html,
  currentIndex,
  loadingMessage,
  onOpenDebugModal,
}: HTMLViewerProps) {
  const htmlFrameRef = useRef<HTMLIFrameElement>(null);
  const { injectKaTeX } = useKaTeXInjection();

  // Update HTML iframe
  useEffect(() => {
    if (!html) return;

    const timer = setTimeout(() => {
      if (htmlFrameRef.current) {
        const iframe = htmlFrameRef.current;
        console.log("Updating iframe with HTML, length:", html.length);

        // Inject KaTeX support if needed
        const htmlWithKaTeX = injectKaTeX(html);

        // Use srcdoc attribute (most reliable method)
        try {
          iframe.srcdoc = htmlWithKaTeX;
          console.log("Iframe srcdoc set successfully with KaTeX support");
        } catch (e) {
          console.warn("srcdoc not supported, using contentDocument:", e);
          // Fallback to contentDocument if srcdoc not supported
          const handleLoad = () => {
            try {
              const doc =
                iframe.contentDocument || iframe.contentWindow?.document;
              if (doc) {
                doc.open();
                doc.write(htmlWithKaTeX);
                doc.close();
                console.log(
                  "Iframe content written via contentDocument with KaTeX support",
                );
              }
            } catch (err) {
              console.error("Failed to write to iframe:", err);
            }
          };

          if (
            iframe.contentDocument &&
            iframe.contentDocument.readyState === "complete"
          ) {
            handleLoad();
          } else {
            iframe.onload = handleLoad;
          }
        }
      } else {
        console.warn("htmlFrameRef.current is null");
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [html, currentIndex, injectKaTeX]);

  if (!html) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center">
        <Loader2 className="w-12 h-12 text-indigo-400 dark:text-indigo-500 animate-spin mb-4" />
        <p className="text-slate-500 dark:text-slate-400">
          {loadingMessage || "Loading learning content..."}
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden relative">
      {/* Debug Button */}
      <button
        onClick={onOpenDebugModal}
        className="absolute top-4 right-4 z-10 p-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg transition-colors shadow-sm"
        title="Fix HTML"
      >
        <Bug className="w-4 h-4 text-slate-600 dark:text-slate-300" />
      </button>

      {/* HTML Content */}
      <iframe
        ref={htmlFrameRef}
        className="w-full h-full border-0"
        title="Interactive Learning Content"
        sandbox="allow-scripts allow-same-origin"
        key={`html-${currentIndex}-${html.length}`}
      />
    </div>
  );
}
