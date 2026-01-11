---
layout: home

hero:
  name: "DeepTutor"
  text: "你的 AI 学习伙伴"
  tagline: 将任何文档转化为互动学习体验
  image:
    src: /logo.png
    alt: DeepTutor
  actions:
    - theme: brand
      text: 快速开始 →
      link: /zh/guide/getting-started
    - theme: alt
      text: GitHub
      link: https://github.com/HKUDS/DeepTutor
    - theme: alt
      text: 🚀 路线图
      link: /zh/roadmap

features:
  - icon: 🧠
    title: 智能解题
    details: 双循环推理架构，提供逐步解答和文档精准引用。
  - icon: 🎯
    title: 题目生成
    details: 基于上传材料生成自定义测验或模拟真实考试。
  - icon: 🎓
    title: 引导学习
    details: 个性化学习路径，配合交互式可视化和自适应讲解。
  - icon: 🔬
    title: 深度研究
    details: 系统化主题探索，整合网络搜索、论文检索和文献综合。
  - icon: 💡
    title: 想法生成
    details: 自动化概念综合和新颖性评估，助力头脑风暴。
  - icon: ✏️
    title: 协作写作
    details: AI 辅助写作，智能编辑、自动标注和语音朗读。
---

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
.VPButton.alt[href="/DeepTutor/zh/roadmap"] {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
  border: none !important;
}

.VPButton.alt[href="/DeepTutor/zh/roadmap"]:hover {
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.5);
  transform: translateY(-2px);
}
</style>
