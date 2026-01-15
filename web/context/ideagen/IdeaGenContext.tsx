"use client";

import React, { createContext, useContext, useState } from "react";
import { IdeaGenState, INITIAL_IDEAGEN_STATE } from "@/types/ideagen";

// Context type
interface IdeaGenContextType {
  ideaGenState: IdeaGenState;
  setIdeaGenState: React.Dispatch<React.SetStateAction<IdeaGenState>>;
}

const IdeaGenContext = createContext<IdeaGenContextType | undefined>(undefined);

export function IdeaGenProvider({ children }: { children: React.ReactNode }) {
  const [ideaGenState, setIdeaGenState] = useState<IdeaGenState>(
    INITIAL_IDEAGEN_STATE,
  );

  return (
    <IdeaGenContext.Provider
      value={{
        ideaGenState,
        setIdeaGenState,
      }}
    >
      {children}
    </IdeaGenContext.Provider>
  );
}

export const useIdeaGen = () => {
  const context = useContext(IdeaGenContext);
  if (!context)
    throw new Error("useIdeaGen must be used within IdeaGenProvider");
  return context;
};
