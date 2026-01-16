"use strict";
import { useState } from "react";
import {
  Database,
  Search,
  FileText,
  Image as ImageIcon,
  X,
  Loader2,
} from "lucide-react";
import { apiUrl } from "@/lib/api";

interface ContentViewModalProps {
  isOpen: boolean;
  onClose: () => void;
  kbName: string;
  content: {
    documents: any[];
    images: any[];
  } | null;
  loading: boolean;
}

export default function ContentViewModal({
  isOpen,
  onClose,
  kbName,
  content,
  loading,
}: ContentViewModalProps) {
  const [activeContentTab, setActiveContentTab] = useState<
    "documents" | "images"
  >("documents");
  const [searchTerm, setSearchTerm] = useState("");
  const [deepSearchResults, setDeepSearchResults] = useState<any[]>([]);
  const [searchingDeep, setSearchingDeep] = useState(false);

  // Helper functions
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 w-full max-w-2xl h-[80vh] shadow-2xl border border-slate-200 dark:border-slate-700 animate-fade-in flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Database className="w-5 h-5 text-blue-500" />
              Knowledge Base Content
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Viewing content for{" "}
              <span className="font-semibold">{kbName}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 dark:border-slate-700 mb-4">
          <button
            onClick={() => setActiveContentTab("documents")}
            className={`pb-3 px-4 text-sm font-medium transition-colors border-b-2 ${
              activeContentTab === "documents"
                ? "border-blue-500 text-blue-600 dark:text-blue-400"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
            }`}
          >
            Documents ({content?.documents.length || 0})
          </button>
          <button
            onClick={() => setActiveContentTab("images")}
            className={`pb-3 px-4 text-sm font-medium transition-colors border-b-2 ${
              activeContentTab === "images"
                ? "border-blue-500 text-blue-600 dark:text-blue-400"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
            }`}
          >
            Images ({content?.images.length || 0})
          </button>
        </div>

        {/* Search */}
        <div className="flex gap-4 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder={`Search ${activeContentTab}...`}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-slate-200 dark:border-slate-600 rounded-xl bg-slate-50 dark:bg-slate-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto min-h-0 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
          ) : !content ||
            (activeContentTab === "documents" &&
              content.documents.length === 0) ||
            (activeContentTab === "images" && content.images.length === 0) ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-400">
              {activeContentTab === "documents" ? (
                <FileText className="w-12 h-12 mb-3 opacity-20" />
              ) : (
                <ImageIcon className="w-12 h-12 mb-3 opacity-20" />
              )}
              <p>No {activeContentTab} found</p>
            </div>
          ) : (
            <>
              {/* Documents View (Table) */}
              {activeContentTab === "documents" && (
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 font-medium border-b border-slate-200 dark:border-slate-700 sticky top-0 z-10">
                    <tr>
                      <th className="px-4 py-3">Name</th>
                      <th className="px-4 py-3 w-24">Size</th>
                      <th className="px-4 py-3 w-40">Modified</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                    {content.documents
                      .filter((item) =>
                        item.name
                          .toLowerCase()
                          .includes(searchTerm.toLowerCase()),
                      )
                      .map((item, i) => (
                        <tr
                          key={i}
                          className="hover:bg-white dark:hover:bg-slate-800/50 transition-colors group"
                        >
                          <td className="px-4 py-3 font-medium text-slate-700 dark:text-slate-200 flex items-center gap-2">
                            <FileText className="w-4 h-4 text-slate-400 group-hover:text-blue-500 transition-colors" />
                            <span
                              className="truncate max-w-[300px]"
                              title={item.name}
                            >
                              {item.name}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-500 dark:text-slate-400 whitespace-nowrap text-xs font-mono">
                            {formatFileSize(item.size)}
                          </td>
                          <td className="px-4 py-3 text-slate-400 dark:text-slate-500 text-xs whitespace-nowrap">
                            {formatDate(item.last_modified)}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              )}

              {/* Images View (Grid) */}
              {activeContentTab === "images" && (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 p-4">
                  {content.images
                    .filter((item) =>
                      item.name
                        .toLowerCase()
                        .includes(searchTerm.toLowerCase()),
                    )
                    .map((item, i) => (
                      <div
                        key={i}
                        className="group relative bg-white dark:bg-slate-800 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700 hover:shadow-md transition-all"
                      >
                        <div className="aspect-square bg-slate-100 dark:bg-slate-900 relative overflow-hidden">
                          <img
                            src={apiUrl(
                              `/api/v1/knowledge/${kbName}/images/${item.name}`,
                            )}
                            alt={item.name}
                            className="w-full h-full object-cover transition-transform group-hover:scale-105 duration-300"
                            loading="lazy"
                          />
                          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                        </div>
                        <div className="p-2 border-t border-slate-100 dark:border-slate-700">
                          <p
                            className="text-xs font-medium text-slate-700 dark:text-slate-200 truncate"
                            title={item.name}
                          >
                            {item.name}
                          </p>
                          <div className="flex justify-between items-center mt-1 text-[10px] text-slate-400">
                            <span>{formatFileSize(item.size || 0)}</span>
                            <span>{formatDate(item.last_modified)}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
