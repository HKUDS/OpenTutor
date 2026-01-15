"use client";

interface LayoutWrapperProps {
  children: React.ReactNode;
}

/**
 * LayoutWrapper - Simplified
 *
 * Previously handled setup wizard display logic.
 * Now just a simple wrapper for children.
 */
export default function LayoutWrapper({ children }: LayoutWrapperProps) {
  return <>{children}</>;
}
