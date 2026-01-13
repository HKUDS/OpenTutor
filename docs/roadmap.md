# Roadmap

## ⚡ Current Focus

- 🔄 **More RAG Pipelines** — Expanding retrieval architectures and backends
-  **Database Robustness & Visualization** — Stability improvements and visual insights
- 🔄 **Bug Fixing** — Addressing reported issues and edge cases

## 📬 Received Feature Wishlist

Community-requested features we're considering:

- 👥 **Multi-user Collaborative Learning** — Real-time shared sessions
- 🎓 **Generalized Guided Learning** — Broader adaptive learning paths
- 📝 **Automatic Note Generation** — AI-powered summary and note creation

---

<div class="community-wrapper">

<div class="community-header">
  <h2>🤝 Shape the Future !</h2>
  <p>DeepTutor is built by the community, for the community.</p>
</div>

<div class="community-grid">

<div class="community-card">
  <div class="card-icon">💡</div>
  <div class="card-title">Ideas</div>
  <div class="card-desc">Share feedback & propose features</div>
  <div class="card-links">
    <div class="link-row">
      <a href="https://discord.gg/zpP9cssj" class="discord">Discord</a>
      <a href="https://github.com/HKUDS/DeepTutor/issues/78" class="wechat">WeChat</a>
    </div>
    <div class="link-row">
      <a href="https://github.com/HKUDS/DeepTutor/discussions" class="github">GitHub Discussions</a>
    </div>
  </div>
</div>

<div class="community-card">
  <div class="card-icon">🔧</div>
  <div class="card-title">Code</div>
  <div class="card-desc">PRs welcome on <code>dev</code> branch</div>
  <div class="card-links">
    <a href="https://github.com/HKUDS/DeepTutor/blob/main/CONTRIBUTING.md" class="github">Contributing Guide →</a>
  </div>
</div>

</div>

</div>

<style>
.community-wrapper {
  margin-top: 24px;
  padding: 40px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%);
  border: 1px solid rgba(102, 126, 234, 0.1);
  border-radius: 16px;
}

.community-header {
  text-align: center;
  margin-bottom: 32px;
}

.community-header h2 {
  margin: 0 0 8px;
  font-size: 1.6rem;
  border: none;
}

.community-header p {
  margin: 0;
  color: var(--vp-c-text-2);
  font-size: 1rem;
}

.community-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  max-width: 600px;
  margin: 0 auto;
}

@media (max-width: 640px) {
  .community-grid {
    grid-template-columns: 1fr;
  }
}

.community-card {
  background: var(--vp-c-bg);
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  transition: all 0.25s ease;
}

.community-card:hover {
  border-color: rgba(102, 126, 234, 0.4);
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.08);
  transform: translateY(-2px);
}

.card-icon {
  font-size: 2rem;
  margin-bottom: 12px;
}

.card-title {
  font-size: 1.15rem;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--vp-c-text-1);
}

.card-desc {
  font-size: 0.9rem;
  color: var(--vp-c-text-2);
  margin-bottom: 16px;
}

.card-links {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.link-row {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.card-links a {
  font-size: 0.85rem;
  font-weight: 500;
  text-decoration: none;
  padding: 6px 14px;
  border-radius: 6px;
  transition: all 0.2s;
}

/* Discord - 蓝紫色 */
.card-links a.discord {
  color: #5865F2;
  background: rgba(88, 101, 242, 0.1);
}
.card-links a.discord:hover {
  background: rgba(88, 101, 242, 0.2);
}

/* WeChat - 绿色 */
.card-links a.wechat {
  color: #07C160;
  background: rgba(7, 193, 96, 0.1);
}
.card-links a.wechat:hover {
  background: rgba(7, 193, 96, 0.2);
}

/* GitHub - 深灰紫 */
.card-links a.github {
  color: #6e5494;
  background: rgba(110, 84, 148, 0.1);
}
.card-links a.github:hover {
  background: rgba(110, 84, 148, 0.2);
}
</style>
