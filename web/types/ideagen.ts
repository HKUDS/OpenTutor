// IdeaGen-specific types

/**
 * Research idea item
 */
export interface ResearchIdea {
  id: string;
  knowledge_point: string;
  description: string;
  research_ideas: string[];
  statement: string;
  expanded: boolean;
  selected: boolean;
}

/**
 * IdeaGen state
 */
export interface IdeaGenState {
  isGenerating: boolean;
  generationStatus: string;
  generatedIdeas: ResearchIdea[];
  progress: { current: number; total: number } | null;
}

/**
 * Initial IdeaGen state
 */
export const INITIAL_IDEAGEN_STATE: IdeaGenState = {
  isGenerating: false,
  generationStatus: "",
  generatedIdeas: [],
  progress: null,
};
