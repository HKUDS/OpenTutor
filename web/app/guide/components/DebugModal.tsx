"use client";

import { useState } from "react";
import { Bug, X, Loader2 } from "lucide-react";

interface DebugModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFix: (description: string) => Promise<boolean>;
}

export default function DebugModal({
  isOpen,
  onClose,
  onFix,
}: DebugModalProps) {
  const [description, setDescription] = useState("");
  const [fixing, setFixing] = useState(false);

  if (!isOpen) return null;

  const handleFix = async () => {
    if (!description.trim() || fixing) return;

    setFixing(true);
    const success = await onFix(description);
    setFixing(false);

    if (success) {
      setDescription("");
      onClose();
    }
  };

  const handleClose = () => {
    setDescription("");
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-in fade-in">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-[500px] animate-in zoom-in-95">
        <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Bug className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            Fix HTML Issue
          </h3>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
          >
            <X className="w-5 h-5 text-slate-500 dark:text-slate-400" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              Issue Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the HTML issue, e.g.: button not clickable, style display error, interaction not working..."
              rows={6}
              className="w-full px-4 py-2 border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-xl focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none resize-none"
            />
          </div>
        </div>
        <div className="p-4 border-t border-slate-100 dark:border-slate-700 flex justify-end gap-2">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleFix}
            disabled={!description.trim() || fixing}
            className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {fixing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Fixing...
              </>
            ) : (
              <>
                <Bug className="w-4 h-4" />
                Fix
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
