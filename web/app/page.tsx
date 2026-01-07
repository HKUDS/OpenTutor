"use client";

import { useState, useEffect } from "react";
import {
  LayoutDashboard,
  History,
  ArrowRight,
  FileText,
  HelpCircle,
  Search,
  Clock,
  ChevronRight,
  Database,
  BookOpen,
  Book,
  Calculator,
  Microscope,
  PenTool,
  Plus,
  Lightbulb,
  LucideIcon,
} from "lucide-react";
import Link from "next/link";
import ActivityDetail from "@/components/ActivityDetail";
import SystemStatus from "@/components/SystemStatus";
import { apiUrl } from "@/lib/api";
import { getTranslation } from "@/lib/i18n";
import { useGlobal } from "@/context/GlobalContext";

// Icon mapping for data-driven UI
const ICON_MAP: Record<string, LucideIcon> = {
  HelpCircle,
  FileText,
  Search,
  PenTool,
  BookOpen,
  Lightbulb,
  LayoutDashboard,
};

// Color mapping for Tailwind classes
const COLOR_MAP: Record<string, string> = {
  blue: "text-blue-500",
  purple: "text-purple-500",
  emerald: "text-emerald-500",
  amber: "text-amber-500",
  indigo: "text-indigo-500",
  yellow: "text-yellow-500",
  slate: "text-slate-500",
};

// Fallback agent config (used if API fails)
const FALLBACK_AGENT_CONFIG: Record<string, AgentConfig> = {
  solve: { icon: "HelpCircle", color: "blue", label_key: "Problem Solved" },
  question: {
    icon: "FileText",
    color: "purple",
    label_key: "Question Generated",
  },
  research: { icon: "Search", color: "emerald", label_key: "Research Report" },
  co_writer: { icon: "PenTool", color: "amber", label_key: "Co-Writer" },
  guide: { icon: "BookOpen", color: "indigo", label_key: "Guided Learning" },
  ideagen: { icon: "Lightbulb", color: "yellow", label_key: "Idea Generated" },
};

interface AgentConfig {
  icon: string;
  color: string;
  label_key: string;
}

interface Activity {
  id: string;
  type: "solve" | "question" | "research";
  title: string;
  summary: string;
  timestamp: number;
  content: any;
}

interface NotebookSummary {
  id: string;
  name: string;
  description: string;
  record_count: number;
  updated_at: number;
  color: string;
}

interface NotebookStats {
  total_notebooks: number;
  total_records: number;
  records_by_type: {
    solve: number;
    question: number;
    research: number;
    co_writer: number;
  };
  recent_notebooks: NotebookSummary[];
}

export default function DashboardPage() {
  const { uiSettings } = useGlobal();
  const t = (key: string) => getTranslation(uiSettings.language, key);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(
    null,
  );
  const [notebookStats, setNotebookStats] = useState<NotebookStats | null>(
    null,
  );
  const [agentConfig, setAgentConfig] = useState<Record<string, AgentConfig>>(
    FALLBACK_AGENT_CONFIG,
  );

  useEffect(() => {
    // Fetch agent configuration
    fetch(apiUrl("/api/v1/config/agents"))
      .then((res) => res.json())
      .then((data) => setAgentConfig(data))
      .catch((err) => {
        console.error("Failed to fetch agent config, using fallback:", err);
      });

    // Fetch activities
    fetch(apiUrl("/api/v1/dashboard/recent?limit=10"))
      .then((res) => res.json())
      .then((data) => setActivities(data))
      .catch((err) => {
        console.error(err);
      })
      .finally(() => setLoading(false));

    // Fetch notebook statistics
    fetch(apiUrl("/api/v1/notebook/statistics"))
      .then((res) => res.json())
      .then((data) => setNotebookStats(data))
      .catch((err) => {
        console.error("Failed to fetch notebook stats:", err);
      });
  }, []);

  // Data-driven icon getter
  const getIcon = (type: string) => {
    const config = agentConfig[type];
    const IconComponent = ICON_MAP[config?.icon] || LayoutDashboard;
    const colorClass = COLOR_MAP[config?.color] || "text-slate-500";
    return <IconComponent className={`w-5 h-5 ${colorClass}`} />;
  };

  // Data-driven label getter
  const getLabel = (type: string) => {
    const config = agentConfig[type];
    return t(config?.label_key || "Activity");
  };

  return (
    <div className="animate-fade-in space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-3">
          <LayoutDashboard className="w-8 h-8 text-blue-600 dark:text-blue-400" />
          {t("Dashboard")}
        </h1>
        <p className="text-slate-500 dark:text-slate-400 mt-2">
          {t("Overview of your recent learning activities")}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left: Recent Activity Feed */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <History className="w-5 h-5 text-slate-400 dark:text-slate-500" />
              {t("Recent Activity")}
            </h2>
            <Link
              href="#"
              className="text-sm text-blue-600 dark:text-blue-400 font-medium hover:underline flex items-center gap-1"
            >
              {t("View All")} <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-700 overflow-hidden">
            {loading ? (
              <div className="p-8 text-center text-slate-400 dark:text-slate-500">
                {t("Loading activities...")}
              </div>
            ) : activities.length === 0 ? (
              <div className="p-12 text-center">
                <div className="w-16 h-16 bg-slate-50 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                  <History className="w-8 h-8 text-slate-300 dark:text-slate-500" />
                </div>
                <p className="text-slate-500 dark:text-slate-400">
                  {t("No recent activity found")}
                </p>
                <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">
                  {t("Start solving problems or generating questions!")}
                </p>
              </div>
            ) : (
              activities.map((activity) => (
                <div
                  key={activity.id}
                  onClick={() => setSelectedActivity(activity)}
                  className="p-5 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors group cursor-pointer"
                >
                  <div className="flex gap-4">
                    <div className="mt-1">
                      <div className="w-10 h-10 rounded-xl bg-slate-50 dark:bg-slate-700 border border-slate-100 dark:border-slate-600 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                        {getIcon(activity.type)}
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start">
                        <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
                          {getLabel(activity.type)}
                        </p>
                        <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(
                            activity.timestamp * 1000,
                          ).toLocaleDateString()}
                        </span>
                      </div>
                      <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 truncate pr-4">
                        {activity.title}
                      </h3>
                      {activity.summary && (
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                          {activity.summary}
                        </p>
                      )}
                      {activity.content?.kb_name && (
                        <div className="mt-3 flex items-center gap-2">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600">
                            <Database className="w-3 h-3 mr-1" />
                            {activity.content.kb_name}
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="self-center opacity-0 group-hover:opacity-100 transition-opacity">
                      <ArrowRight className="w-5 h-5 text-slate-400 dark:text-slate-500" />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right: Quick Actions / Stats */}
        <div className="space-y-6">
          {/* Notebooks Overview */}
          <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl p-6 text-white shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <Book className="w-5 h-5" />
                {t("My Notebooks")}
              </h3>
              <Link
                href="/notebook"
                className="text-xs text-white/80 hover:text-white flex items-center gap-1"
              >
                {t("View All")} <ChevronRight className="w-3 h-3" />
              </Link>
            </div>

            {notebookStats ? (
              <>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="bg-white/10 rounded-xl p-3">
                    <div className="text-2xl font-bold">
                      {notebookStats.total_notebooks}
                    </div>
                    <div className="text-xs text-white/70">
                      {t("Notebooks")}
                    </div>
                  </div>
                  <div className="bg-white/10 rounded-xl p-3">
                    <div className="text-2xl font-bold">
                      {notebookStats.total_records}
                    </div>
                    <div className="text-xs text-white/70">{t("records")}</div>
                  </div>
                </div>

                {/* Records by type */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 text-white/80">
                      <Calculator className="w-3 h-3" /> {t("Solve")}
                    </span>
                    <span className="font-medium">
                      {notebookStats.records_by_type.solve}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 text-white/80">
                      <FileText className="w-3 h-3" /> {t("Question")}
                    </span>
                    <span className="font-medium">
                      {notebookStats.records_by_type.question}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 text-white/80">
                      <Microscope className="w-3 h-3" /> {t("Research")}
                    </span>
                    <span className="font-medium">
                      {notebookStats.records_by_type.research}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 text-white/80">
                      <PenTool className="w-3 h-3" /> {t("Co-Writer")}
                    </span>
                    <span className="font-medium">
                      {notebookStats.records_by_type.co_writer}
                    </span>
                  </div>
                </div>

                {/* Recent notebooks */}
                {notebookStats.recent_notebooks.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-white/20">
                    <div className="text-xs text-white/60 mb-2">Recent</div>
                    <div className="space-y-2">
                      {notebookStats.recent_notebooks.slice(0, 3).map((nb) => (
                        <Link
                          key={nb.id}
                          href="/notebook"
                          className="flex items-center gap-2 p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors"
                        >
                          <div
                            className="w-6 h-6 rounded flex items-center justify-center"
                            style={{ backgroundColor: nb.color }}
                          >
                            <BookOpen className="w-3 h-3 text-white" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate">
                              {nb.name}
                            </div>
                            <div className="text-[10px] text-white/60">
                              {nb.record_count} records
                            </div>
                          </div>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-4">
                <BookOpen className="w-8 h-8 mx-auto mb-2 text-white/40" />
                <p className="text-sm text-white/60">{t("No notebooks yet")}</p>
                <Link
                  href="/notebook"
                  className="mt-2 inline-flex items-center gap-1 text-xs text-white/80 hover:text-white"
                >
                  <Plus className="w-3 h-3" /> {t("Create your first notebook")}
                </Link>
              </div>
            )}
          </div>

          {/* System Status */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
            <h3 className="font-bold text-slate-900 dark:text-slate-100 mb-4">
              {t("System Status")}
            </h3>
            <SystemStatus />
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
            <h3 className="font-bold text-slate-900 dark:text-slate-100 mb-4">
              {t("Quick Actions")}
            </h3>
            <div className="space-y-3">
              <Link
                href="/solver"
                className="block w-full p-3 rounded-xl bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors text-sm flex items-center gap-3"
              >
                <div className="p-1.5 bg-white dark:bg-slate-700 rounded-lg shadow-sm">
                  <HelpCircle className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                </div>
                {t("Ask a Question")}
              </Link>
              <Link
                href="/question"
                className="block w-full p-3 rounded-xl bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 font-medium hover:bg-purple-100 dark:hover:bg-purple-900/50 transition-colors text-sm flex items-center gap-3"
              >
                <div className="p-1.5 bg-white dark:bg-slate-700 rounded-lg shadow-sm">
                  <FileText className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                </div>
                {t("Generate Quiz")}
              </Link>
              <Link
                href="/research"
                className="block w-full p-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 font-medium hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition-colors text-sm flex items-center gap-3"
              >
                <div className="p-1.5 bg-white dark:bg-slate-700 rounded-lg shadow-sm">
                  <Search className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                </div>
                {t("Start Research")}
              </Link>
            </div>
          </div>
        </div>
      </div>

      {selectedActivity && (
        <ActivityDetail
          activity={selectedActivity}
          onClose={() => setSelectedActivity(null)}
        />
      )}
    </div>
  );
}
