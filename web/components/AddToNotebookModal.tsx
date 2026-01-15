"use client";

import { useState, useEffect } from "react";
import {
  X,
  BookOpen,
  Plus,
  Check,
  Loader2,
  Book,
  FolderOpen,
} from "lucide-react";
import { apiUrl } from "@/lib/api";

interface NotebookOption {
  id: string;
  name: string;
  description: string;
  color: string;
  record_count: number;
}

interface AddToNotebookModalProps {
  isOpen: boolean;
  onClose: () => void;
  recordType: "solve" | "question" | "research" | "co_writer" | "chat";
  title: string;
  userQuery: string;
  output: string;
  metadata?: Record<string, any>;
  kbName?: string;
}

const COLORS = [
  "#3B82F6",
  "#8B5CF6",
  "#EC4899",
  "#EF4444",
  "#F97316",
  "#EAB308",
  "#22C55E",
  "#14B8A6",
  "#06B6D4",
  "#6366F1",
];

export default function AddToNotebookModal({
  isOpen,
  onClose,
  recordType,
  title,
  userQuery,
  output,
  metadata = {},
  kbName,
}: AddToNotebookModalProps) {
  const [notebooks, setNotebooks] = useState<NotebookOption[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newNotebook, setNewNotebook] = useState({
    name: "",
    description: "",
    color: "#3B82F6",
  });
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchNotebooks();
      setSelectedIds([]);
      setSuccess(false);
      setShowCreateForm(false);
    }
  }, [isOpen]);

  const fetchNotebooks = async () => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl("/api/v1/notebook/list"));
      const data = await res.json();
      setNotebooks(data.notebooks || []);
    } catch (err) {
      console.error("Failed to fetch notebooks:", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleNotebook = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    );
  };

  const handleCreateNotebook = async () => {
    if (!newNotebook.name.trim()) return;

    try {
      const res = await fetch(apiUrl("/api/v1/notebook/create"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newNotebook),
      });
      const data = await res.json();
      if (data.success && data.notebook) {
        await fetchNotebooks();
        setSelectedIds((prev) => [...prev, data.notebook.id]);
        setShowCreateForm(false);
        setNewNotebook({ name: "", description: "", color: "#3B82F6" });
      }
    } catch (err) {
      console.error("Failed to create notebook:", err);
    }
  };

  const handleSave = async () => {
    if (selectedIds.length === 0) return;

    setSaving(true);
    try {
      const res = await fetch(apiUrl("/api/v1/notebook/add_record"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notebook_ids: selectedIds,
          record_type: recordType,
          title,
          user_query: userQuery,
          output,
          metadata,
          kb_name: kbName,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setSuccess(true);
        setTimeout(() => {
          onClose();
        }, 1500);
      }
    } catch (err) {
      console.error("Failed to add record:", err);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-in fade-in">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-[480px] max-h-[80vh] flex flex-col animate-in zoom-in-95">
        {/* Header */}
        <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/30 dark:to-purple-900/30 rounded-t-2xl">
          <h3 className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Book className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            Add to Notebook
          </h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/50 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-500 dark:text-slate-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {success ? (
            <div className="py-12 text-center animate-in zoom-in-95">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/40 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              <h4 className="text-lg font-bold text-slate-900 dark:text-slate-100 mb-1">
                Added Successfully!
              </h4>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Record has been saved to {selectedIds.length} notebook
                {selectedIds.length > 1 ? "s" : ""}
              </p>
            </div>
          ) : loading ? (
            <div className="py-12 text-center">
              <Loader2 className="w-8 h-8 text-indigo-600 dark:text-indigo-400 animate-spin mx-auto mb-2" />
              <p className="text-slate-500 dark:text-slate-400">
                Loading notebooks...
              </p>
            </div>
          ) : (
            <>
              {/* Record Preview */}
              <div className="mb-4 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl border border-slate-100 dark:border-slate-600">
                <div className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                  Record Preview
                </div>
                <h4 className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                  {title}
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mt-1">
                  {userQuery}
                </p>
              </div>

              {/* Notebook Selection */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Select Notebooks
                  </label>
                  <button
                    onClick={() => setShowCreateForm(!showCreateForm)}
                    className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" />
                    New Notebook
                  </button>
                </div>

                {/* Create New Notebook Form */}
                {showCreateForm && (
                  <div className="mb-3 p-3 bg-indigo-50 dark:bg-indigo-900/30 rounded-xl border border-indigo-100 dark:border-indigo-800 animate-in slide-in-from-top-2">
                    <input
                      type="text"
                      value={newNotebook.name}
                      onChange={(e) =>
                        setNewNotebook((prev) => ({
                          ...prev,
                          name: e.target.value,
                        }))
                      }
                      placeholder="Notebook name"
                      className="w-full px-3 py-2 mb-2 border border-indigo-200 dark:border-indigo-700 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100"
                      autoFocus
                    />
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        Color:
                      </span>
                      <div className="flex gap-1">
                        {COLORS.slice(0, 6).map((color) => (
                          <button
                            key={color}
                            onClick={() =>
                              setNewNotebook((prev) => ({ ...prev, color }))
                            }
                            className={`w-5 h-5 rounded transition-all ${
                              newNotebook.color === color
                                ? "ring-2 ring-offset-1 ring-slate-400 dark:ring-slate-500 dark:ring-offset-slate-800 scale-110"
                                : ""
                            }`}
                            style={{ backgroundColor: color }}
                          />
                        ))}
                      </div>
                    </div>
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setShowCreateForm(false)}
                        className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 rounded-lg transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleCreateNotebook}
                        disabled={!newNotebook.name.trim()}
                        className="px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" />
                        Create
                      </button>
                    </div>
                  </div>
                )}

                {/* Notebook List */}
                {notebooks.length === 0 ? (
                  <div className="py-8 text-center">
                    <FolderOpen className="w-10 h-10 text-slate-200 dark:text-slate-600 mx-auto mb-2" />
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                      No notebooks yet
                    </p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">
                      Create your first notebook above
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[240px] overflow-y-auto">
                    {notebooks.map((nb) => (
                      <button
                        key={nb.id}
                        onClick={() => toggleNotebook(nb.id)}
                        className={`w-full p-3 rounded-xl flex items-center gap-3 transition-all border-2 text-left ${
                          selectedIds.includes(nb.id)
                            ? "bg-indigo-50 dark:bg-indigo-900/30 border-indigo-300 dark:border-indigo-700"
                            : "bg-white dark:bg-slate-700/50 border-slate-200 dark:border-slate-600 hover:border-indigo-200 dark:hover:border-indigo-700 hover:bg-slate-50 dark:hover:bg-slate-700"
                        }`}
                      >
                        <div
                          className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                          style={{
                            backgroundColor: `${nb.color}20`,
                            color: nb.color,
                          }}
                        >
                          <BookOpen className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h4 className="font-semibold text-slate-900 dark:text-slate-100 truncate text-sm">
                            {nb.name}
                          </h4>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            {nb.record_count} records
                          </p>
                        </div>
                        <div
                          className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-all ${
                            selectedIds.includes(nb.id)
                              ? "bg-indigo-600 border-indigo-600"
                              : "border-slate-300 dark:border-slate-500"
                          }`}
                        >
                          {selectedIds.includes(nb.id) && (
                            <Check className="w-3 h-3 text-white" />
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {!success && !loading && (
          <div className="p-4 border-t border-slate-100 dark:border-slate-700 flex justify-between items-center">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {selectedIds.length > 0
                ? `${selectedIds.length} notebook${selectedIds.length > 1 ? "s" : ""} selected`
                : "Select at least one notebook"}
            </span>
            <div className="flex gap-2">
              <button
                onClick={onClose}
                className="px-4 py-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={selectedIds.length === 0 || saving}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 text-sm flex items-center gap-2"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Book className="w-4 h-4" />
                    Add to Notebook
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
