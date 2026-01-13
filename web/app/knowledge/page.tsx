"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  BookOpen,
  Database,
  FileText,
  FolderOpen,
  Image as ImageIcon,
  Layers,
  Link,
  Unlink,
  MoreVertical,
  Plus,
  Search,
  Upload,
  Trash2,
  Loader2,
  X,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { apiUrl, wsUrl } from "@/lib/api";

interface KnowledgeBase {
  name: string;
  is_default: boolean;
  statistics: {
    raw_documents: number;
    images: number;
    content_lists: number;
    rag_initialized: boolean;
    rag?: {
      chunks?: number;
      entities?: number;
      relations?: number;
    };
  };
}

interface ProgressInfo {
  stage: string;
  message: string;
  current: number;
  total: number;
  file_name?: string;
  progress_percent: number;
  error?: string;
}

interface LinkedFolder {
  id: string;
  path: string;
  added_at: string;
  file_count: number;
  last_sync?: string;
}

interface FolderChanges {
  has_changes: boolean;
  new_count: number;
  modified_count: number;
}

export default function KnowledgePage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [targetKb, setTargetKb] = useState<string>("");
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState<FileList | null>(null);
  const [newKbName, setNewKbName] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [progressMap, setProgressMap] = useState<Record<string, ProgressInfo>>(
    {},
  );
  // Link Folder feature (Issue #101)
  const [linkFolderModalOpen, setLinkFolderModalOpen] = useState(false);
  const [folderPath, setFolderPath] = useState("");
  const [linking, setLinking] = useState(false);
  const [linkedFoldersMap, setLinkedFoldersMap] = useState<
    Record<string, LinkedFolder[]>
  >({});
  const [folderChangesMap, setFolderChangesMap] = useState<
    Record<string, FolderChanges>
  >({});
  const [syncingFolders, setSyncingFolders] = useState<Set<string>>(new Set());
  // Use ref only for WebSocket connections (no need for state as it's not used in render)
  const wsConnectionsRef = useRef<Record<string, WebSocket>>({});
  const kbsNamesRef = useRef<string[]>([]);

  // Restore progress state from localStorage (with cleanup of stuck states)
  useEffect(() => {
    try {
      const saved = localStorage.getItem("kb_progress_map");
      if (saved) {
        const parsed = JSON.parse(saved);

        // Clean up stuck progress states (older than 30 minutes and not completed/error)
        const now = new Date().getTime();
        const thirtyMinutes = 30 * 60 * 1000;
        const cleaned: Record<string, ProgressInfo> = {};

        Object.entries(parsed).forEach(([kbName, progress]: [string, any]) => {
          if (progress.timestamp) {
            const progressTime = new Date(progress.timestamp).getTime();
            const age = now - progressTime;

            // Keep if: completed, error, or recent (< 30 min)
            if (
              progress.stage === "completed" ||
              progress.stage === "error" ||
              age < thirtyMinutes
            ) {
              cleaned[kbName] = progress;
            } else {
              console.log(
                `[KB Progress] Clearing stuck progress for ${kbName} (age: ${Math.round(age / 60000)} min)`,
              );
            }
          } else {
            // No timestamp, keep completed/error, clear others
            if (progress.stage === "completed" || progress.stage === "error") {
              cleaned[kbName] = progress;
            }
          }
        });

        setProgressMap(cleaned);
        localStorage.setItem("kb_progress_map", JSON.stringify(cleaned));
      }
    } catch (e) {
      console.error("Failed to load progress from localStorage:", e);
    }
  }, []);

  // Persist progress state to localStorage
  useEffect(() => {
    try {
      localStorage.setItem("kb_progress_map", JSON.stringify(progressMap));
    } catch (e) {
      console.error("Failed to save progress to localStorage:", e);
    }
  }, [progressMap]);

  // Define fetchKnowledgeBases using useCallback to ensure it's available
  const fetchKnowledgeBases = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const baseUrl = apiUrl("");
      const listUrl = apiUrl("/api/v1/knowledge/list");
      const healthUrl = apiUrl("/api/v1/knowledge/health");

      console.log("🔍 Fetching knowledge bases...");
      console.log("  Base URL:", baseUrl);
      console.log("  List URL:", listUrl);
      console.log("  Health URL:", healthUrl);

      // Test health check endpoint first
      try {
        const healthRes = await fetch(healthUrl);
        const healthData = await healthRes.json();
        console.log("✅ Health check response:", healthData);
      } catch (healthErr) {
        console.warn("⚠️ Health check failed:", healthErr);
      }

      // Fetch knowledge base list
      const res = await fetch(listUrl, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      console.log("📡 Response status:", res.status, res.statusText);
      console.log(
        "📡 Response headers:",
        Object.fromEntries(res.headers.entries()),
      );

      if (!res.ok) {
        let errorMessage = `HTTP ${res.status}: Failed to fetch knowledge bases`;
        let errorDetail = "";
        try {
          const errorData = await res.json();
          errorDetail = errorData.detail || errorData.message || "";
          errorMessage = errorDetail || errorMessage;
          console.error("❌ Error response:", errorData);
        } catch (parseErr) {
          const text = await res.text();
          console.error("❌ Error response (text):", text);
          errorMessage = `${errorMessage}. Response: ${text.substring(0, 200)}`;
        }
        throw new Error(errorMessage);
      }

      const data = await res.json();
      console.log("✅ Received knowledge bases:", data);
      console.log("✅ Data type:", Array.isArray(data) ? "array" : typeof data);
      console.log("✅ Data length:", Array.isArray(data) ? data.length : "N/A");

      if (!Array.isArray(data)) {
        throw new Error(
          `Invalid response format: expected array, got ${typeof data}`,
        );
      }

      setKbs(data);
      setError(null); // Clear previous error - empty list is not an error, it's just empty state
    } catch (err: any) {
      console.error("❌ Error fetching knowledge bases:", err);
      console.error("❌ Error stack:", err.stack);

      let errorMessage =
        err.message ||
        "Failed to load knowledge bases. Please ensure the backend is running.";

      // Provide more detailed message for network errors
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        errorMessage = `Network error: Cannot connect to backend at ${apiUrl("")}. Please ensure the backend is running.`;
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKnowledgeBases();
  }, [fetchKnowledgeBases]);

  // Establish WebSocket connections for all KBs to receive progress updates (only when KB names change)
  useEffect(() => {
    // Skip if still loading or kbs is not yet loaded
    if (loading || !kbs) {
      return;
    }

    // Only re-establish connections if KB names actually changed
    const currentKbNames = [...kbs.map((kb) => kb.name)].sort();
    const currentKbNamesStr = currentKbNames.join(",");
    const prevKbNames = [...(kbsNamesRef.current || [])].sort();
    const prevKbNamesStr = prevKbNames.join(",");

    // If KB names haven't changed, don't re-establish connections
    if (
      currentKbNamesStr === prevKbNamesStr &&
      currentKbNamesStr !== "" &&
      Object.keys(wsConnectionsRef.current).length > 0
    ) {
      // Update statistics in existing connections context, but don't reconnect
      return;
    }

    // If kbs is empty and we have connections, close them all
    if (kbs.length === 0) {
      if (Object.keys(wsConnectionsRef.current).length > 0) {
        Object.values(wsConnectionsRef.current).forEach((ws) => {
          if (
            ws &&
            (ws.readyState === WebSocket.OPEN ||
              ws.readyState === WebSocket.CONNECTING)
          ) {
            ws.close();
          }
        });
        wsConnectionsRef.current = {};
      }
      kbsNamesRef.current = [];
      return;
    }

    // Close old connections that are no longer needed
    Object.entries(wsConnectionsRef.current).forEach(([kbName, ws]) => {
      if (!kbs.find((kb) => kb.name === kbName)) {
        if (
          ws &&
          (ws.readyState === WebSocket.OPEN ||
            ws.readyState === WebSocket.CONNECTING)
        ) {
          ws.close();
        }
        delete wsConnectionsRef.current[kbName];
      }
    });

    const connections: Record<string, WebSocket> = {
      ...wsConnectionsRef.current,
    };

    kbs.forEach((kb) => {
      // Only create new connection if one doesn't exist
      if (
        connections[kb.name] &&
        connections[kb.name].readyState !== WebSocket.CLOSED
      ) {
        return;
      }
      // Connect to all KBs (not just uninitialized ones)
      // This allows receiving progress updates when adding documents
      const ws = new WebSocket(
        wsUrl(`/api/v1/knowledge/${kb.name}/progress/ws`),
      );

      ws.onopen = () => {
        console.log(`[Progress WS] Connected for KB: ${kb.name}`);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "progress" && data.data) {
            // If KB is already initialized (ready), ignore stale in-progress updates
            // Only accept 'completed' or 'error' or recent updates (within 5 minutes)
            if (kb.statistics.rag_initialized) {
              const progressStage = data.data.stage;
              const progressTime = data.data.timestamp
                ? new Date(data.data.timestamp).getTime()
                : 0;
              const now = new Date().getTime();
              const fiveMinutes = 5 * 60 * 1000;

              // Skip stale in-progress updates for already-ready KBs
              if (progressStage !== "completed" && progressStage !== "error") {
                if (!progressTime || now - progressTime > fiveMinutes) {
                  console.log(
                    `[Progress WS] Ignoring stale progress for ready KB: ${kb.name}`,
                  );
                  return;
                }
              }
            }

            setProgressMap((prev) => {
              const updated = {
                ...prev,
                [kb.name]: data.data,
              };
              // Auto-persist to localStorage
              try {
                localStorage.setItem(
                  "kb_progress_map",
                  JSON.stringify(updated),
                );
              } catch (e) {
                console.error("Failed to save progress to localStorage:", e);
              }
              return updated;
            });

            // Don't auto-refresh KB list when completed or error
            // User can manually refresh using the refresh button
          } else if (data.type === "error") {
            console.error(
              `[Progress WS] Error for KB ${kb.name}:`,
              data.message,
            );
          }
        } catch (e) {
          console.error(
            `[Progress WS] Error parsing message for ${kb.name}:`,
            e,
          );
        }
      };

      ws.onerror = (error) => {
        console.error(`[Progress WS] Error for ${kb.name}:`, error);
      };

      ws.onclose = () => {
        console.log(`[Progress WS] Closed for KB: ${kb.name}`);
      };

      connections[kb.name] = ws;
      wsConnectionsRef.current[kb.name] = ws;
    });

    kbsNamesRef.current = kbs.map((kb) => kb.name);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kbs, loading]);

  // Cleanup all connections on component unmount
  useEffect(() => {
    return () => {
      Object.values(wsConnectionsRef.current).forEach((ws) => {
        if (
          ws &&
          (ws.readyState === WebSocket.OPEN ||
            ws.readyState === WebSocket.CONNECTING)
        ) {
          ws.close();
        }
      });
      wsConnectionsRef.current = {};
    };
  }, []);

  const handleDelete = async (name: string) => {
    if (
      !confirm(
        `Are you sure you want to delete knowledge base "${name}"? This cannot be undone.`,
      )
    )
      return;

    try {
      const res = await fetch(apiUrl(`/api/v1/knowledge/${name}`), {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete knowledge base");

      // Also clear progress state for this KB
      clearProgress(name);

      fetchKnowledgeBases();
    } catch (err) {
      console.error(err);
      alert("Failed to delete knowledge base");
    }
  };

  // Clear progress state for a specific KB (frontend + backend)
  const clearProgress = async (kbName: string) => {
    // Clear frontend state
    setProgressMap((prev) => {
      const updated = { ...prev };
      delete updated[kbName];
      try {
        localStorage.setItem("kb_progress_map", JSON.stringify(updated));
      } catch (e) {
        console.error("Failed to save progress to localStorage:", e);
      }
      return updated;
    });

    // Clear backend progress file
    try {
      await fetch(apiUrl(`/api/v1/knowledge/${kbName}/progress/clear`), {
        method: "POST",
      });
      console.log(`[Progress] Cleared backend progress for KB: ${kbName}`);
    } catch (e) {
      console.error("Failed to clear backend progress:", e);
    }
  };

  // Clear all stuck progress states
  const clearAllStuckProgress = () => {
    setProgressMap((prev) => {
      const cleaned: Record<string, ProgressInfo> = {};
      Object.entries(prev).forEach(([kbName, progress]) => {
        // Only keep completed and error states
        if (progress.stage === "completed" || progress.stage === "error") {
          cleaned[kbName] = progress;
        }
      });
      try {
        localStorage.setItem("kb_progress_map", JSON.stringify(cleaned));
      } catch (e) {
        console.error("Failed to save progress to localStorage:", e);
      }
      return cleaned;
    });
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!files || files.length === 0 || !targetKb) return;

    setUploading(true);
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("files", file);
    });

    try {
      const res = await fetch(apiUrl(`/api/v1/knowledge/${targetKb}/upload`), {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");

      setUploadModalOpen(false);
      setFiles(null);
      // Refresh immediately to establish WebSocket connection
      await fetchKnowledgeBases();
      alert("Files uploaded successfully! Processing started in background.");
    } catch (err) {
      console.error(err);
      alert("Failed to upload files");
    } finally {
      setUploading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKbName || !files || files.length === 0) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("name", newKbName);
    Array.from(files).forEach((file) => {
      formData.append("files", file);
    });

    try {
      const res = await fetch(apiUrl("/api/v1/knowledge/create"), {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Creation failed");
      }

      const result = await res.json();

      // Immediately display new KB in frontend (optimistic update)
      const newKb: KnowledgeBase = {
        name: result.name,
        is_default: false,
        statistics: {
          raw_documents: result.files?.length || 0,
          images: 0,
          content_lists: 0,
          rag_initialized: false,
        },
      };

      // Add to list (if not exists)
      setKbs((prev) => {
        const exists = prev.some((kb) => kb.name === newKb.name);
        if (exists) {
          return prev;
        }
        return [newKb, ...prev];
      });

      // Initialize progress state
      setProgressMap((prev) => ({
        ...prev,
        [newKb.name]: {
          stage: "initializing",
          message: "Initializing knowledge base...",
          current: 0,
          total: 0,
          file_name: "",
          progress_percent: 0,
          timestamp: new Date().toISOString(),
        },
      }));

      setCreateModalOpen(false);
      setFiles(null);
      setNewKbName("");

      // Delay refresh to get full info (but user can already see the new KB)
      setTimeout(async () => {
        await fetchKnowledgeBases();
      }, 1000);

      alert(
        "Knowledge base created successfully! Initialization started in background.",
      );
    } catch (err: any) {
      console.error(err);
      alert(`Failed to create knowledge base: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFiles(e.dataTransfer.files);
    }
  }, []);

  // Handle linking a local folder to a KB (Issue #101)
  const handleLinkFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!folderPath || !targetKb) return;

    setLinking(true);
    try {
      // Link the folder
      const linkRes = await fetch(
        apiUrl(`/api/v1/knowledge/${targetKb}/link-folder`),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ folder_path: folderPath }),
        },
      );

      if (!linkRes.ok) {
        const errorData = await linkRes.json();
        throw new Error(errorData.detail || "Failed to link folder");
      }

      const folderInfo = await linkRes.json();

      // Trigger sync to process the files
      const syncRes = await fetch(
        apiUrl(`/api/v1/knowledge/${targetKb}/sync-folder/${folderInfo.id}`),
        { method: "POST" },
      );

      if (!syncRes.ok) {
        console.warn("Folder linked but sync failed");
      }

      setLinkFolderModalOpen(false);
      setFolderPath("");
      await fetchKnowledgeBases();
      await fetchLinkedFolders(targetKb);

      alert(
        `Folder linked successfully! Found ${folderInfo.file_count} documents. Processing started in background.`,
      );
    } catch (err: any) {
      console.error(err);
      alert(`Failed to link folder: ${err.message}`);
    } finally {
      setLinking(false);
    }
  };

  // Fetch linked folders for a knowledge base
  const fetchLinkedFolders = useCallback(async (kbName: string) => {
    try {
      const res = await fetch(
        apiUrl(`/api/v1/knowledge/${kbName}/linked-folders`),
      );
      if (res.ok) {
        const folders: LinkedFolder[] = await res.json();
        setLinkedFoldersMap((prev) => ({ ...prev, [kbName]: folders }));

        // Check for changes in each folder
        for (const folder of folders) {
          try {
            const changesRes = await fetch(
              apiUrl(
                `/api/v1/knowledge/${kbName}/linked-folders/${folder.id}/changes`,
              ),
            );
            if (changesRes.ok) {
              const changes: FolderChanges = await changesRes.json();
              setFolderChangesMap((prev) => ({
                ...prev,
                [`${kbName}:${folder.id}`]: changes,
              }));
            }
          } catch (e) {
            console.warn(`Failed to check changes for folder ${folder.id}:`, e);
          }
        }
      }
    } catch (err) {
      console.warn(`Failed to fetch linked folders for ${kbName}:`, err);
    }
  }, []);

  // Sync a linked folder (process new/modified files)
  const handleSyncFolder = async (kbName: string, folderId: string) => {
    const syncKey = `${kbName}:${folderId}`;
    setSyncingFolders((prev) => new Set(prev).add(syncKey));

    try {
      const res = await fetch(
        apiUrl(`/api/v1/knowledge/${kbName}/sync-folder/${folderId}`),
        { method: "POST" },
      );

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Sync failed");
      }

      const result = await res.json();
      await fetchKnowledgeBases();
      await fetchLinkedFolders(kbName);

      if (result.file_count === 0) {
        alert("No new or modified files to sync.");
      } else {
        alert(
          `Syncing ${result.file_count} files (${result.new_files || 0} new, ${result.modified_files || 0} modified). Processing in background.`,
        );
      }
    } catch (err: any) {
      console.error("Sync error:", err);
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncingFolders((prev) => {
        const next = new Set(prev);
        next.delete(syncKey);
        return next;
      });
    }
  };

  // Unlink a folder from a knowledge base
  const handleUnlinkFolder = async (
    kbName: string,
    folderId: string,
    folderPath: string,
  ) => {
    if (
      !confirm(
        `Are you sure you want to unlink "${folderPath}"?\n\nNote: This will only remove the folder link. Documents already processed will remain in the knowledge base.`,
      )
    ) {
      return;
    }

    try {
      const res = await fetch(
        apiUrl(`/api/v1/knowledge/${kbName}/linked-folders/${folderId}`),
        { method: "DELETE" },
      );

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to unlink folder");
      }

      await fetchLinkedFolders(kbName);
      alert("Folder unlinked successfully.");
    } catch (err: any) {
      console.error("Unlink error:", err);
      alert(`Failed to unlink folder: ${err.message}`);
    }
  };

  // Fetch linked folders when KBs are loaded
  useEffect(() => {
    if (kbs.length > 0) {
      kbs.forEach((kb) => {
        fetchLinkedFolders(kb.name);
      });
    }
  }, [kbs, fetchLinkedFolders]);

  return (
    <div className="animate-fade-in h-screen overflow-y-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-3">
            <BookOpen className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            Knowledge Bases
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-2">
            Manage and explore your educational content repositories.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={async () => {
              setLoading(true);
              await fetchKnowledgeBases();
            }}
            className="bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors flex items-center gap-2 border border-slate-200 dark:border-slate-600 shadow-sm hover:shadow"
            title="Refresh knowledge bases"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={() => {
              setFiles(null);
              setNewKbName("");
              setCreateModalOpen(true);
            }}
            className="bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-800 dark:hover:bg-slate-200 transition-colors flex items-center gap-2 shadow-lg shadow-slate-900/20"
          >
            <Plus className="w-4 h-4" />
            New Knowledge Base
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 p-4 rounded-xl border border-red-100 dark:border-red-800 mb-6 flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-white dark:bg-slate-800 h-48 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* KB Grid */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {kbs.map((kb) => (
            <div
              key={kb.name}
              className="group bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md transition-all duration-300 hover:-translate-y-1 overflow-hidden flex flex-col"
            >
              {/* Card Header */}
              <div className="p-6 border-b border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 flex justify-between items-start">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-white dark:bg-slate-700 rounded-xl border border-slate-200 dark:border-slate-600 flex items-center justify-center shadow-sm">
                    <Database className="w-5 h-5 text-blue-500 dark:text-blue-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 dark:text-slate-100">
                      {kb.name}
                    </h3>
                    {kb.is_default && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 text-[10px] font-bold uppercase tracking-wide border border-blue-100 dark:border-blue-800 mt-1">
                        Default
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => {
                      setTargetKb(kb.name);
                      setFiles(null);
                      setUploadModalOpen(true);
                    }}
                    className="p-2 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                    title="Upload Documents"
                  >
                    <Upload className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      setTargetKb(kb.name);
                      setFolderPath("");
                      setLinkFolderModalOpen(true);
                    }}
                    className="p-2 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg text-slate-500 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
                    title="Link Local Folder"
                  >
                    <FolderOpen className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(kb.name)}
                    className="p-2 hover:bg-red-100 dark:hover:bg-red-900/40 rounded-lg text-slate-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                    title="Delete Knowledge Base"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Stats */}
              <div className="p-6 space-y-4 flex-1">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-slate-50 dark:bg-slate-700/50 p-3 rounded-lg">
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-medium mb-1 flex items-center gap-1.5">
                      <FileText className="w-3 h-3" /> Documents
                    </p>
                    <p className="text-lg font-bold text-slate-700 dark:text-slate-200">
                      {kb.statistics.raw_documents}
                    </p>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-700/50 p-3 rounded-lg">
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-medium mb-1 flex items-center gap-1.5">
                      <ImageIcon className="w-3 h-3" /> Images
                    </p>
                    <p className="text-lg font-bold text-slate-700 dark:text-slate-200">
                      {kb.statistics.images}
                    </p>
                  </div>
                </div>

                <div className="pt-2">
                  <div className="flex items-center justify-between text-xs mb-2">
                    <span className="text-slate-500 dark:text-slate-400 font-medium flex items-center gap-1.5">
                      <Layers className="w-3 h-3" /> Status
                    </span>
                    {(() => {
                      const progress = progressMap[kb.name];
                      if (progress) {
                        if (progress.stage === "completed") {
                          return (
                            <span className="text-emerald-600 dark:text-emerald-400 font-bold">
                              Ready
                            </span>
                          );
                        } else if (progress.stage === "error") {
                          return (
                            <span className="text-red-600 dark:text-red-400 font-bold">
                              Error
                            </span>
                          );
                        } else {
                          // Display current stage and progress
                          const stageLabels: Record<string, string> = {
                            initializing: "Initializing",
                            processing_documents: "Processing",
                            processing_file: "Processing File",
                            extracting_items: "Extracting Items",
                          };
                          const stageLabel =
                            stageLabels[progress.stage] || progress.stage;
                          return (
                            <span className="text-blue-600 dark:text-blue-400 font-bold flex items-center gap-1">
                              <Loader2 className="w-3 h-3 animate-spin" />
                              {stageLabel} {progress.progress_percent}%
                            </span>
                          );
                        }
                      }
                      return (
                        <span
                          className={
                            kb.statistics.rag_initialized
                              ? "text-emerald-600 dark:text-emerald-400 font-bold"
                              : "text-slate-400 dark:text-slate-500"
                          }
                        >
                          {kb.statistics.rag_initialized
                            ? "Ready"
                            : "Not Indexed"}
                        </span>
                      );
                    })()}
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden">
                    {(() => {
                      const progress = progressMap[kb.name];
                      if (progress) {
                        const percent = progress.progress_percent;
                        let bgColor = "bg-blue-500";
                        if (progress.stage === "completed") {
                          bgColor = "bg-emerald-500";
                        } else if (progress.stage === "error") {
                          bgColor = "bg-red-500";
                        }
                        return (
                          <div
                            className={`h-full rounded-full ${bgColor} transition-all duration-300`}
                            style={{ width: `${percent}%` }}
                          />
                        );
                      }
                      return (
                        <div
                          className={`h-full rounded-full ${kb.statistics.rag_initialized ? "bg-emerald-500 w-full" : "bg-slate-300 w-0"}`}
                        />
                      );
                    })()}
                  </div>
                  {(() => {
                    const progress = progressMap[kb.name];
                    if (progress && progress.message) {
                      return (
                        <div className="mt-2 space-y-1">
                          <div className="text-[10px] text-slate-600 dark:text-slate-400 font-medium flex items-center justify-between">
                            <span>{progress.message}</span>
                            {/* Clear button for stuck states */}
                            {progress.stage !== "completed" && (
                              <button
                                onClick={async (e) => {
                                  e.stopPropagation();
                                  await clearProgress(kb.name);
                                  // Refresh KB list to show correct status
                                  fetchKnowledgeBases();
                                }}
                                className="text-slate-400 dark:text-slate-500 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                                title="Clear progress status"
                              >
                                <X className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                          {progress.file_name && (
                            <div className="text-[10px] text-slate-500 dark:text-slate-400 flex items-center gap-1">
                              <FileText className="w-3 h-3" />
                              <span className="truncate">
                                {progress.file_name}
                              </span>
                            </div>
                          )}
                          {progress.current > 0 && progress.total > 0 && (
                            <div className="text-[10px] text-slate-400 dark:text-slate-500">
                              File {progress.current} of {progress.total}
                            </div>
                          )}
                          {progress.error && (
                            <div className="text-[10px] text-red-600 dark:text-red-400 mt-1">
                              Error: {progress.error}
                            </div>
                          )}
                        </div>
                      );
                    }
                    if (kb.statistics.rag) {
                      return (
                        <div className="mt-2 flex gap-3 text-[10px] text-slate-400 dark:text-slate-500">
                          <span>{kb.statistics.rag.chunks} chunks</span>
                          <span>•</span>
                          <span>{kb.statistics.rag.entities} entities</span>
                        </div>
                      );
                    }
                    return null;
                  })()}
                </div>

                {/* Linked Folders Section */}
                {linkedFoldersMap[kb.name] &&
                  linkedFoldersMap[kb.name].length > 0 && (
                    <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
                      <div className="flex items-center gap-1.5 mb-3">
                        <FolderOpen className="w-3.5 h-3.5 text-emerald-500" />
                        <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                          Linked Folders
                        </span>
                        <span className="text-[10px] text-slate-400 dark:text-slate-500">
                          ({linkedFoldersMap[kb.name].length})
                        </span>
                      </div>
                      <div className="space-y-2">
                        {linkedFoldersMap[kb.name].map((folder) => {
                          const syncKey = `${kb.name}:${folder.id}`;
                          const changes = folderChangesMap[syncKey];
                          const isSyncing = syncingFolders.has(syncKey);
                          const hasChanges =
                            changes?.has_changes &&
                            (changes.new_count > 0 ||
                              changes.modified_count > 0);

                          return (
                            <div
                              key={folder.id}
                              className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-2.5 group/folder"
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300 font-medium">
                                    <FolderOpen className="w-3 h-3 flex-shrink-0 text-slate-400" />
                                    <span
                                      className="truncate"
                                      title={folder.path}
                                    >
                                      {folder.path.length > 30
                                        ? `...${folder.path.slice(-27)}`
                                        : folder.path}
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2 mt-1">
                                    <span className="text-[10px] text-slate-400 dark:text-slate-500">
                                      {folder.file_count} files
                                    </span>
                                    {hasChanges && (
                                      <span className="inline-flex items-center gap-0.5 text-[10px] text-amber-600 dark:text-amber-400 font-medium">
                                        <AlertCircle className="w-2.5 h-2.5" />
                                        {changes.new_count > 0 &&
                                          `${changes.new_count} new`}
                                        {changes.new_count > 0 &&
                                          changes.modified_count > 0 &&
                                          ", "}
                                        {changes.modified_count > 0 &&
                                          `${changes.modified_count} modified`}
                                      </span>
                                    )}
                                    {!hasChanges && folder.last_sync && (
                                      <span className="inline-flex items-center gap-0.5 text-[10px] text-emerald-600 dark:text-emerald-400">
                                        <CheckCircle2 className="w-2.5 h-2.5" />
                                        Synced
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="flex items-center gap-1 opacity-0 group-hover/folder:opacity-100 transition-opacity">
                                  <button
                                    onClick={() =>
                                      handleSyncFolder(kb.name, folder.id)
                                    }
                                    disabled={isSyncing}
                                    className={`p-1.5 rounded-md transition-colors ${
                                      isSyncing
                                        ? "bg-blue-100 dark:bg-blue-900/40 text-blue-500"
                                        : "hover:bg-blue-100 dark:hover:bg-blue-900/40 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400"
                                    }`}
                                    title="Sync folder"
                                  >
                                    <RefreshCw
                                      className={`w-3.5 h-3.5 ${isSyncing ? "animate-spin" : ""}`}
                                    />
                                  </button>
                                  <button
                                    onClick={() =>
                                      handleUnlinkFolder(
                                        kb.name,
                                        folder.id,
                                        folder.path,
                                      )
                                    }
                                    className="p-1.5 hover:bg-red-100 dark:hover:bg-red-900/40 rounded-md text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                                    title="Unlink folder"
                                  >
                                    <Unlink className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-2 italic">
                        💡 Hover to see sync/unlink actions
                      </p>
                    </div>
                  )}
              </div>
            </div>
          ))}

          {/* Empty State */}
          {kbs.length === 0 && (
            <div className="col-span-full text-center py-12 text-slate-400 dark:text-slate-500">
              <Database className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No knowledge bases found. Create one to get started.</p>
            </div>
          )}
        </div>
      )}

      {/* Create KB Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 ">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md p-6 animate-in zoom-in-95">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                Create Knowledge Base
              </h3>
              <button
                onClick={() => setCreateModalOpen(false)}
                className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Knowledge Base Name
                </label>
                <input
                  type="text"
                  required
                  value={newKbName}
                  onChange={(e) => setNewKbName(e.target.value)}
                  placeholder="e.g., Math101"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Upload Documents
                </label>
                <div
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                    dragActive
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30"
                      : "border-slate-200 dark:border-slate-600 hover:border-blue-400 dark:hover:border-blue-500 bg-slate-50 dark:bg-slate-700/50"
                  }`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <input
                    type="file"
                    multiple
                    className="hidden"
                    id="kb-file-upload"
                    onChange={(e) => setFiles(e.target.files)}
                    accept=".pdf,.txt,.md"
                  />
                  <label
                    htmlFor="kb-file-upload"
                    className="cursor-pointer flex flex-col items-center gap-2"
                  >
                    <Upload
                      className={`w-8 h-8 ${dragActive ? "text-blue-500 dark:text-blue-400" : "text-slate-400 dark:text-slate-500"}`}
                    />
                    <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                      {files && files.length > 0
                        ? `${files.length} files selected`
                        : "Drag & drop files here or click to browse"}
                    </span>
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      Supports PDF, TXT, MD
                    </span>
                  </label>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 font-medium hover:bg-slate-50 dark:hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={
                    !newKbName || !files || files.length === 0 || uploading
                  }
                  className="flex-1 py-2.5 rounded-xl bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-medium hover:bg-slate-800 dark:hover:bg-slate-200 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {uploading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    "Create & Initialize"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Upload Modal (Existing) */}
      {uploadModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md p-6 animate-in zoom-in-95">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                Upload Documents
              </h3>
              <button
                onClick={() => setUploadModalOpen(false)}
                className="text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
              Upload PDF, TXT, or MD files to{" "}
              <strong className="text-slate-700 dark:text-slate-200">
                {targetKb}
              </strong>
              .
            </p>

            <form onSubmit={handleUpload} className="space-y-4">
              <div className="border-2 border-dashed border-slate-200 dark:border-slate-600 rounded-xl p-8 text-center hover:border-blue-400 dark:hover:border-blue-500 transition-colors bg-slate-50 dark:bg-slate-700/50">
                <input
                  type="file"
                  multiple
                  className="hidden"
                  id="file-upload"
                  onChange={(e) => setFiles(e.target.files)}
                  accept=".pdf,.txt,.md"
                />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer flex flex-col items-center gap-2"
                >
                  <Upload className="w-8 h-8 text-slate-400 dark:text-slate-500" />
                  <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                    {files && files.length > 0
                      ? `${files.length} files selected`
                      : "Click to browse files"}
                  </span>
                </label>
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(false)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 font-medium hover:bg-slate-50 dark:hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!files || uploading}
                  className="flex-1 py-2.5 rounded-xl bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {uploading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    "Upload"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Link Folder Modal (Issue #101) */}
      {linkFolderModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 w-full max-w-md shadow-2xl border border-slate-200 dark:border-slate-700 animate-fade-in">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <FolderOpen className="w-5 h-5 text-emerald-500" />
                Link Local Folder
              </h2>
              <button
                onClick={() => setLinkFolderModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
              Link a local folder to{" "}
              <span className="font-semibold text-slate-700 dark:text-slate-200">
                {targetKb}
              </span>
              . Documents in the folder will be processed and added to this
              knowledge base.
            </p>

            <form onSubmit={handleLinkFolder} className="space-y-4">
              <div>
                <label
                  htmlFor="folder-path"
                  className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1"
                >
                  Folder Path
                </label>
                <input
                  type="text"
                  id="folder-path"
                  value={folderPath}
                  onChange={(e) => setFolderPath(e.target.value)}
                  placeholder="Paste or type the full folder path"
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl bg-slate-50 dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-slate-400 dark:text-slate-500">
                    <strong>macOS/Linux:</strong> ~/Documents/papers or
                    /Users/name/folder
                  </p>
                  <p className="text-xs text-slate-400 dark:text-slate-500">
                    <strong>Windows:</strong> C:\Users\name\Documents\papers
                  </p>
                </div>
              </div>

              <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
                <p className="text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">
                  📄 Supported files: PDF, DOCX, TXT, MD
                </p>
                <p className="text-[10px] text-slate-400 dark:text-slate-500">
                  New and modified files will be automatically detected when you
                  sync.
                </p>
              </div>

              <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-3 border border-emerald-100 dark:border-emerald-800">
                <p className="text-xs text-emerald-700 dark:text-emerald-400">
                  <strong>💡 Tip:</strong> Use folders synced with Google Drive,
                  OneDrive, SharePoint, or Dropbox for automatic cloud
                  integration.
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setLinkFolderModalOpen(false)}
                  className="flex-1 py-2.5 rounded-xl border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 font-medium hover:bg-slate-50 dark:hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!folderPath || linking}
                  className="flex-1 py-2.5 rounded-xl bg-emerald-600 text-white font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {linking ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Link className="w-4 h-4" />
                      Link Folder
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
