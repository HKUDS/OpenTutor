// Sidebar-specific types

/**
 * Sidebar navigation order configuration
 */
export interface SidebarNavOrder {
  start: string[]; // Array of href paths for START group
  learnResearch: string[]; // Array of href paths for LEARN & RESEARCH group
}

/**
 * Sidebar constants
 */
export const SIDEBAR_MIN_WIDTH = 64;
export const SIDEBAR_MAX_WIDTH = 320;
export const SIDEBAR_DEFAULT_WIDTH = 256;
export const SIDEBAR_COLLAPSED_WIDTH = 64;

/**
 * Default sidebar description
 */
export const DEFAULT_SIDEBAR_DESCRIPTION = "✨ Data Intelligence Lab @ HKU";

/**
 * Default navigation order
 */
export const DEFAULT_NAV_ORDER: SidebarNavOrder = {
  start: ["/", "/history", "/knowledge", "/notebook"],
  learnResearch: [
    "/question",
    "/solver",
    "/guide",
    "/ideagen",
    "/research",
    "/co_writer",
  ],
};
