"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  Home,
  History,
  BookOpen,
  PenTool,
  Calculator,
  Microscope,
  Edit3,
  Settings,
  Book,
  GraduationCap,
  Lightbulb,
  Github,
  Globe,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useGlobal } from "@/context/GlobalContext";
import { getTranslation } from "@/lib/i18n";

const SIDEBAR_EXPANDED_WIDTH = 256;
const SIDEBAR_COLLAPSED_WIDTH = 64;

export default function Sidebar() {
  const pathname = usePathname();
  const { uiSettings, sidebarCollapsed, toggleSidebar } = useGlobal();
  const lang = uiSettings.language;

  const t = (key: string) => getTranslation(lang, key);

  const [showTooltip, setShowTooltip] = useState<string | null>(null);

  const navGroups = [
    {
      name: "",
      items: [
        { name: t("Home"), href: "/", icon: Home },
        { name: t("History"), href: "/history", icon: History },
        { name: t("Knowledge Bases"), href: "/knowledge", icon: BookOpen },
        { name: t("Notebooks"), href: "/notebook", icon: Book },
      ],
    },
    {
      name: t("Learn"),
      items: [
        { name: t("Question Generator"), href: "/question", icon: PenTool },
        { name: t("Smart Solver"), href: "/solver", icon: Calculator },
        { name: t("Guided Learning"), href: "/guide", icon: GraduationCap },
      ],
    },
    {
      name: t("Research"),
      items: [
        { name: t("IdeaGen"), href: "/ideagen", icon: Lightbulb },
        { name: t("Deep Research"), href: "/research", icon: Microscope },
        { name: t("Co-Writer"), href: "/co_writer", icon: Edit3 },
      ],
    },
  ];

  const currentWidth = sidebarCollapsed
    ? SIDEBAR_COLLAPSED_WIDTH
    : SIDEBAR_EXPANDED_WIDTH;

  // Collapsed sidebar
  if (sidebarCollapsed) {
    return (
      <div
        className="relative flex-shrink-0 bg-slate-50/80 dark:bg-slate-800/80 h-full border-r border-slate-200 dark:border-slate-700 flex flex-col"
        style={{ width: SIDEBAR_COLLAPSED_WIDTH }}
      >
        {/* Header */}
        <div className="px-2 py-3 border-b border-slate-100 dark:border-slate-700 flex justify-center">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden">
            <Image
              src="/logo.png"
              alt="DeepTutor Logo"
              width={32}
              height={32}
              className="object-contain"
              priority
            />
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-2 space-y-1">
          {navGroups.map((group, idx) => (
            <div key={idx} className="space-y-0.5 px-2">
              {group.items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <div key={item.href} className="relative">
                    <Link
                      href={item.href}
                      className={`group flex items-center justify-center p-2 rounded-md border ${
                        isActive
                          ? "bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm border-slate-100 dark:border-slate-600"
                          : "text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 hover:text-blue-600 dark:hover:text-blue-400 hover:shadow-sm border-transparent hover:border-slate-100 dark:hover:border-slate-600"
                      }`}
                      onMouseEnter={() => setShowTooltip(item.href)}
                      onMouseLeave={() => setShowTooltip(null)}
                    >
                      <item.icon
                        className={`w-5 h-5 flex-shrink-0 ${
                          isActive
                            ? "text-blue-500 dark:text-blue-400"
                            : "text-slate-400 dark:text-slate-500 group-hover:text-blue-500 dark:group-hover:text-blue-400"
                        }`}
                      />
                    </Link>
                    {showTooltip === item.href && (
                      <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-50 px-2.5 py-1.5 bg-slate-900 dark:bg-slate-700 text-white text-xs rounded-lg shadow-lg whitespace-nowrap pointer-events-none">
                        {item.name}
                        <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-900 dark:border-r-slate-700" />
                      </div>
                    )}
                  </div>
                );
              })}
              {idx < navGroups.length - 1 && (
                <div className="h-px bg-slate-200 dark:bg-slate-700 my-2" />
              )}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-2 py-2 border-t border-slate-100 dark:border-slate-700 bg-slate-50/30 dark:bg-slate-800/30">
          <div className="relative">
            <Link
              href="/settings"
              className={`flex items-center justify-center p-2 rounded-md ${
                pathname === "/settings"
                  ? "bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm border border-slate-100 dark:border-slate-600"
                  : "text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-slate-100"
              }`}
              onMouseEnter={() => setShowTooltip("/settings")}
              onMouseLeave={() => setShowTooltip(null)}
            >
              <Settings
                className={`w-5 h-5 flex-shrink-0 ${
                  pathname === "/settings"
                    ? "text-blue-500 dark:text-blue-400"
                    : "text-slate-400 dark:text-slate-500"
                }`}
              />
            </Link>
            {showTooltip === "/settings" && (
              <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-50 px-2.5 py-1.5 bg-slate-900 dark:bg-slate-700 text-white text-xs rounded-lg shadow-lg whitespace-nowrap pointer-events-none">
                {t("Settings")}
                <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-900 dark:border-r-slate-700" />
              </div>
            )}
          </div>

          {/* Expand button at bottom */}
          <button
            onClick={toggleSidebar}
            className="w-full mt-2 flex items-center justify-center p-2 rounded-md text-slate-400 dark:text-slate-500 hover:bg-white dark:hover:bg-slate-700 hover:text-blue-500 dark:hover:text-blue-400 hover:shadow-sm border border-transparent hover:border-slate-100 dark:hover:border-slate-600"
            title={t("Expand sidebar")}
          >
            <ChevronsRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  // Expanded sidebar
  return (
    <div
      className="relative flex-shrink-0 bg-slate-50/80 dark:bg-slate-800/80 h-full border-r border-slate-200 dark:border-slate-700 flex flex-col"
      style={{ width: currentWidth }}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700">
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden">
                <Image
                  src="/logo.png"
                  alt="DeepTutor Logo"
                  width={32}
                  height={32}
                  className="object-contain"
                  priority
                />
              </div>
              <h1 className="font-bold text-slate-900 dark:text-slate-100 tracking-tight text-base truncate">
                DeepTutor
              </h1>
            </div>
            <div className="flex items-center gap-0.5">
              {/* Collapse button */}
              <button
                onClick={toggleSidebar}
                className="text-slate-400 hover:text-blue-500 dark:hover:text-blue-400 p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
                title={t("Collapse sidebar")}
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>
              <a
                href="https://hkuds.github.io/DeepTutor/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-400 hover:text-blue-500 dark:hover:text-blue-400 p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
                title="Visit DeepTutor Homepage"
              >
                <Globe className="w-4 h-4" />
              </a>
              <a
                href="https://github.com/HKUDS/DeepTutor"
                target="_blank"
                rel="noopener noreferrer"
                className="text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
                title="View on GitHub"
              >
                <Github className="w-4 h-4" />
              </a>
            </div>
          </div>

          <div className="text-[10px] font-medium text-slate-500 dark:text-slate-400 bg-slate-100/50 dark:bg-slate-700/50 px-2 py-1.5 rounded-md border border-slate-100 dark:border-slate-600 truncate">
            ✨ Data Intelligence Lab @ HKU
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
        {navGroups.map((group, idx) => (
          <div key={idx}>
            {group.name && (
              <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-3 mb-1 truncate">
                {group.name}
              </div>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`group flex items-center gap-2.5 px-3 py-1.5 rounded-md border ${
                      isActive
                        ? "bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm border-slate-100 dark:border-slate-600"
                        : "text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 hover:text-blue-600 dark:hover:text-blue-400 hover:shadow-sm border-transparent hover:border-slate-100 dark:hover:border-slate-600"
                    }`}
                  >
                    <item.icon
                      className={`w-4 h-4 flex-shrink-0 ${
                        isActive
                          ? "text-blue-500 dark:text-blue-400"
                          : "text-slate-400 dark:text-slate-500 group-hover:text-blue-500 dark:group-hover:text-blue-400"
                      }`}
                    />
                    <span className="font-medium text-sm truncate">
                      {item.name}
                    </span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-slate-100 dark:border-slate-700 bg-slate-50/30 dark:bg-slate-800/30">
        <Link
          href="/settings"
          className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm ${
            pathname === "/settings"
              ? "bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm border border-slate-100 dark:border-slate-600"
              : "text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-slate-100"
          }`}
        >
          <Settings
            className={`w-4 h-4 flex-shrink-0 ${
              pathname === "/settings"
                ? "text-blue-500 dark:text-blue-400"
                : "text-slate-400 dark:text-slate-500"
            }`}
          />
          <span>{t("Settings")}</span>
        </Link>
      </div>
    </div>
  );
}
