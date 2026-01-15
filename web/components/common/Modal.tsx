"use client";

import { useEffect, useCallback } from "react";
import { X } from "lucide-react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  titleIcon?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: "sm" | "md" | "lg" | "xl";
  closeOnBackdrop?: boolean;
  closeOnEscape?: boolean;
}

const widthClasses = {
  sm: "w-[400px]",
  md: "w-[500px]",
  lg: "w-[600px]",
  xl: "w-[800px]",
};

/**
 * Shared Modal base component
 */
export default function Modal({
  isOpen,
  onClose,
  title,
  titleIcon,
  children,
  footer,
  width = "md",
  closeOnBackdrop = true,
  closeOnEscape = true,
}: ModalProps) {
  // Handle escape key
  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (closeOnEscape && e.key === "Escape") {
        onClose();
      }
    },
    [closeOnEscape, onClose],
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [isOpen, handleEscape]);

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (closeOnBackdrop && e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-in fade-in"
      onClick={handleBackdropClick}
    >
      <div
        className={`bg-white dark:bg-slate-800 rounded-2xl shadow-2xl ${widthClasses[width]} max-h-[90vh] flex flex-col animate-in zoom-in-95`}
      >
        {/* Header */}
        {(title || titleIcon) && (
          <div className="p-4 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between shrink-0">
            <h3 className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              {titleIcon}
              {title}
            </h3>
            <button
              onClick={onClose}
              className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-slate-500 dark:text-slate-400" />
            </button>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="p-4 border-t border-slate-100 dark:border-slate-700 shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
