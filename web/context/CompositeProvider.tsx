"use client";

import React from "react";
import { SolverProvider } from "./solver";
import { QuestionProvider } from "./question";
import { ResearchProvider } from "./research";
import { ChatProvider } from "./chat";
import { UISettingsProvider, SidebarProvider } from "./settings";
import { IdeaGenProvider } from "./ideagen";

/**
 * CompositeProvider combines all context providers into a single component.
 * This simplifies the provider hierarchy in the app layout.
 */
export function CompositeProvider({ children }: { children: React.ReactNode }) {
  return (
    <UISettingsProvider>
      <SidebarProvider>
        <SolverProvider>
          <QuestionProvider>
            <ResearchProvider>
              <ChatProvider>
                <IdeaGenProvider>{children}</IdeaGenProvider>
              </ChatProvider>
            </ResearchProvider>
          </QuestionProvider>
        </SolverProvider>
      </SidebarProvider>
    </UISettingsProvider>
  );
}
