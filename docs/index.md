---
layout: home

hero:
  name: "DeepTutor"
  text: "Your AI Learning Companion"
  tagline: Transform any document into an interactive learning experience
  image:
    src: /logo.png
    alt: DeepTutor
  actions:
    - theme: brand
      text: Quick Start →
      link: /guide/getting-started
    - theme: alt
      text: GitHub
      link: https://github.com/HKUDS/DeepTutor
    - theme: alt
      text: 🚀 Roadmap
      link: /roadmap

features:
  - icon: 📚
    title: Massive Document Q&A
    details: Upload textbooks, papers, and manuals. Build AI-powered knowledge repositories with RAG and knowledge graph integration.
  - icon: 🎨
    title: Interactive Visualization
    details: Transform complex concepts into visual aids with step-by-step breakdowns and engaging interactive demonstrations.
  - icon: 🧠
    title: Smart Problem Solving
    details: Dual-loop reasoning with step-by-step solutions and precise citations from your documents.
  - icon: 🎯
    title: Practice Generator
    details: Generate custom quizzes or mimic real exams from your uploaded materials.
  - icon: 🎓
    title: Guided Learning
    details: Personalized learning paths with interactive visualizations and adaptive explanations.
  - icon: 🔬
    title: Deep Research
    details: Systematic topic exploration with web search, paper retrieval, and literature synthesis.
  - icon: 💡
    title: Idea Generation
    details: Automated and interactive concept development with multi-source insights and novelty evaluation.
---

## Why DeepTutor?

DeepTutor transforms how students interact with educational materials through a unified multi-agent architecture. Unlike traditional tools, it provides:

- **Deep Understanding** - Not just answers, but guided learning journeys with visual explanations
- **Multi-Modal Support** - PDF, LaTeX, images, code execution, and more
- **Knowledge Graph** - Semantic connections powered by LightRAG for better comprehension
- **All-in-One Platform** - Problem solving, question generation, research, and idea generation

## Quick Demo

```bash
# Clone and setup
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# Install dependencies
bash scripts/install_all.sh

# Start the application
python scripts/start_web.py
```

<style>
:root {
  --vp-home-hero-name-color: transparent;
  --vp-home-hero-name-background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
  --vp-home-hero-image-background-image: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 50%, rgba(240, 147, 251, 0.15) 100%);
  --vp-home-hero-image-filter: blur(68px);
}

.dark {
  --vp-home-hero-image-background-image: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 50%, rgba(240, 147, 251, 0.1) 100%);
}

/* DeepTutor 标题更大 */
.VPHero .name {
  font-size: 4rem !important;
  line-height: 1.1 !important;
}

.VPHero .text {
  font-size: 2.2rem !important;
  font-weight: 600 !important;
  color: var(--vp-c-text-1);
}

@media (max-width: 768px) {
  .VPHero .name {
    font-size: 2.8rem !important;
  }
  .VPHero .text {
    font-size: 1.6rem !important;
  }
}

/* Hero 区域 Roadmap 按钮特殊样式 */
.VPButton.alt[href="/DeepTutor/roadmap"] {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
  border: none !important;
}

.VPButton.alt[href="/DeepTutor/roadmap"]:hover {
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.5);
  transform: translateY(-2px);
}
</style>
