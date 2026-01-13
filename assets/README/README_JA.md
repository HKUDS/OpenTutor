<div align="center">

<img src="../../assets/logo-ver2.png" alt="DeepTutor Logo" width="150" style="border-radius: 15px;">

# DeepTutor: あなたのパーソナル学習アシスタント

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-AGPL--3.0-blue?style=flat-square)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join-7289DA?style=flat&logo=discord&logoColor=white)](https://discord.gg/aka9p9EW)
[![Feishu](https://img.shields.io/badge/Feishu-Group-blue?style=flat)](./Communication.md)
[![WeChat](https://img.shields.io/badge/WeChat-Group-green?style=flat&logo=wechat)](./Communication.md)



[**クイックスタート**](#クイックスタート) · [**コアモジュール**](#コアモジュール) · [**よくある質問**](#よくある質問)

[🇬🇧 English](../../README.md) · [🇨🇳 中文](README_CN.md) · [🇪🇸 Español](README_ES.md) · [🇫🇷 Français](README_FR.md) · [🇸🇦 العربية](README_AR.md) · [🇷🇺 Русский](README_RU.md) · [🇮🇳 हिन्दी](README_HI.md) · [🇵🇹 Português](README_PT.md)

</div>

<div align="center">

| ⚡ **大規模ドキュメント知識Q&A**  |  📈 **インタラクティブ学習可視化**  | <br>
| 🧠 **知識強化**  |  🔬 **深い研究とアイデア生成** |

</div>

---
> **[2026.1.1]** 新年あけましておめでとうございます！[GitHub Discussions](https://github.com/HKUDS/DeepTutor/discussions) に参加して、DeepTutor の未来を一緒に創りましょう！💬

> **[2025.12.30]** 詳細は [公式ウェブサイト](https://hkuds.github.io/DeepTutor/) をご覧ください！

> **[2025.12.29]** DeepTutor v0.1 がリリースされました！✨
---

## DeepTutor の主要機能

### 📚 大規模ドキュメント知識Q&A
• **スマート知識ベース**：教科書、研究論文、技術マニュアル、ドメイン固有のドキュメントをアップロード。包括的な AI 駆動の知識リポジトリを構築し、即座にアクセス可能にします。<br>
• **マルチエージェント問題解決**：RAG、ウェブ検索、論文検索、コード実行を統合したデュアルループ推論アーキテクチャ—正確な引用付きの段階的なソリューションを提供します。

### 🎨 インタラクティブ学習可視化
• **知識の簡素化と説明**：複雑な概念、知識、アルゴリズムを理解しやすい視覚補助、詳細な段階的分解、魅力的なインタラクティブデモンストレーションに変換します。<br>
• **パーソナライズされたQ&A**：学習の進捗に適応するコンテキスト対応の会話、インタラクティブページとセッションベースの知識追跡を提供します。

### 🎯 練習問題生成器による知識強化
• **インテリジェントな演習作成**：現在の知識レベルと特定の学習目標に合わせて、ターゲットを絞ったクイズ、練習問題、カスタマイズされた評価を生成します。<br>
• **本格的な試験シミュレーション**：参考試験をアップロードして、元のスタイル、形式、難易度に完全に一致する練習問題を生成—実際のテストのための現実的な準備を提供します。

### 🔍 深い研究とアイデア生成
• **包括的な研究と文献レビュー**：系統的な分析による深いトピック探索を実施。パターンを識別し、分野を超えた関連概念を接続し、既存の研究結果を統合します。<br>
• **新しい洞察の発見**：構造化された学習資料を生成し、知識のギャップを発見します。インテリジェントなクロスドメイン知識統合を通じて、有望な新しい研究方向を特定します。

---

<div align="center">
  <img src="../../assets/figs/title_gradient.svg" alt="All-in-One Tutoring System" width="70%">
</div>

<br>

<!-- ━━━━━━━━━━━━━━━━ Core Learning Experience ━━━━━━━━━━━━━━━━ -->

<table>
<tr>
<td width="50%" align="center" valign="top">

<h3>📚 大規模ドキュメント知識Q&A</h3>
<a href="#problem-solving-agent">
<img src="../../assets/gifs/solve.gif" width="100%">
</a>
<br>
<sub>正確な引用を伴うマルチエージェント問題解決</sub>

</td>
<td width="50%" align="center" valign="top">

<h3>🎨 インタラクティブ学習可視化</h3>
<a href="#guided-learning">
<img src="../../assets/gifs/guided-learning.gif" width="100%">
</a>
<br>
<sub>パーソナライズされたQ&Aを備えたステップバイステップの視覚的説明</sub>

</td>
</tr>
</table>

<!-- ━━━━━━━━━━━━━━━━ Practice & Reinforcement ━━━━━━━━━━━━━━━━ -->

<h3 align="center">🎯 知識強化</h3>

<table>
<tr>
<td width="50%" valign="top" align="center">

<a href="#question-generator">
<img src="../../assets/gifs/question-1.gif" width="100%">
</a>

**カスタム質問**  
<sub>自動検証された練習問題の生成</sub>

</td>
<td width="50%" valign="top" align="center">

<a href="#question-generator">
<img src="../../assets/gifs/question-2.gif" width="100%">
</a>

**模擬質問**  
<sub>本格的な練習のための試験スタイルのクローン</sub>

</td>
</tr>
</table>

<!-- ━━━━━━━━━━━━━━━━ Research & Creation ━━━━━━━━━━━━━━━━ -->

<h3 align="center">🔍 深い研究とアイデア生成</h3>

<table>
<tr>
<td width="33%" align="center">

<a href="#deep-research">
<img src="../../assets/gifs/deepresearch.gif" width="100%">
</a>

**深い研究**  
<sub>RAG、ウェブ、論文検索による教科書からの知識拡張</sub>

</td>
<td width="33%" align="center">

<a href="#idea-generation">
<img src="../../assets/gifs/ideagen.gif" width="100%">
</a>

**自動化されたアイデア生成**  
<sub>デュアルフィルターワークフローによる系統的なブレインストーミングと概念統合</sub>

</td>
<td width="33%" align="center">

<a href="#co-writer">
<img src="../../assets/gifs/co-writer.gif" width="100%">
</a>

**インタラクティブなアイデア生成**  
<sub>ポッドキャスト生成を備えたRAGとウェブ検索駆動のCo-Writer</sub>

</td>
</tr>
</table>

<!-- ━━━━━━━━━━━━━━━━ Knowledge Infrastructure ━━━━━━━━━━━━━━━━ -->

<h3 align="center">🏗️ オールインワン知識システム</h3>

<table>
<tr>
<td width="50%" align="center">

<a href="#dashboard--knowledge-base-management">
<img src="../../assets/gifs/knowledge_bases.png" width="100%">
</a>

**個人知識ベース**  
<sub>独自の知識リポジトリを構築・整理</sub>

</td>
<td width="50%" align="center">

<a href="#notebook">
<img src="../../assets/gifs/notebooks.png" width="100%">
</a>

**個人ノートブック**  
<sub>学習セッションのコンテキストメモリ</sub>

</td>
</tr>
</table>

<p align="center">
  <sub>🌙 <b>ダークモード</b> で DeepTutor を使用！</sub>
</p>

---

## 🏛️ DeepTutor のフレームワーク

<div align="center">
<img src="../../assets/figs/full-pipe.png" alt="DeepTutor Full-Stack Workflow" width="100%">
</div>

### 💬 ユーザーインターフェース層
• **直感的なインタラクション**：直感的なインタラクションのためのシンプルな双方向クエリ-レスポンスフロー。<br>
• **構造化された出力**：複雑な情報を実行可能な出力に整理する構造化レスポンス生成。

### 🤖 インテリジェントエージェントモジュール
• **問題解決と評価**：段階的な問題解決とカスタム評価生成。<br>
• **研究と学習**：トピック探索のための深い研究と可視化を備えたガイド付き学習。<br>
• **アイデア生成**：マルチソースの洞察を備えた自動化およびインタラクティブな概念開発。

### 🔧 ツール統合層
• **情報検索**：RAG ハイブリッド検索、リアルタイムウェブ検索、学術論文データベース。<br>
• **処理と分析**：Python コード実行、クエリ項目検索、ドキュメント分析のための PDF 解析。

### 🧠 知識とメモリ基盤
• **知識グラフ**：セマンティック接続と知識発見のためのエンティティ-関係マッピング。<br>
• **ベクトルストア**：インテリジェントなコンテンツ検索のための埋め込みベースのセマンティック検索。<br>
• **メモリシステム**：コンテキストの継続性のためのセッション状態管理と引用追跡。

## 📋 タスク

> 🌟 今後の更新をフォローするために Star してください！
- [ ] ローカル LLM サービスのサポート（例：ollama）
- [ ] RAG モジュールのリファクタリング（[Discussions](https://github.com/HKUDS/DeepTutor/discussions) を参照）
- [ ] アイデア生成からの深いコーディング
- [ ] ノートブックとのパーソナライズされたインタラクション

## 🚀 クイックスタート

### ステップ 1: 事前設定

**① リポジトリをクローン**

```bash
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor
```

**② 環境変数を設定**

```bash
cp .env.example .env
# API キーで .env ファイルを編集
```

<details>
<summary>📋 <b>環境変数リファレンス</b></summary>

| 変数 | 必須 | 説明 |
|:---|:---:|:---|
| `LLM_MODEL` | **はい** | モデル名（例：`gpt-4o`） |
| `LLM_API_KEY` | **はい** | LLM API キー |
| `LLM_HOST` | **はい** | API エンドポイント URL |
| `EMBEDDING_MODEL` | **はい** | 埋め込みモデル名 |
| `EMBEDDING_API_KEY` | **はい** | 埋め込み API キー |
| `EMBEDDING_HOST` | **はい** | 埋め込み API エンドポイント |
| `BACKEND_PORT` | いいえ | バックエンドポート（デフォルト：`8001`） |
| `FRONTEND_PORT` | いいえ | フロントエンドポート（デフォルト：`3782`） |
| `TTS_*` | いいえ | テキスト読み上げ設定 |
| `PERPLEXITY_API_KEY` | いいえ | ウェブ検索用 |

</details>

**③ ポートと LLM を設定** *(オプション)*

- **ポート**：`config/main.yaml` を編集 → `server.backend_port` / `server.frontend_port`
- **LLM**：`config/agents.yaml` を編集 → 各モジュールの `temperature` / `max_tokens`
- 詳細は[設定ドキュメント](config/README.md)を参照

**④ デモナレッジベースを試す** *(オプション)*

<details>
<summary>📚 <b>利用可能なデモ</b></summary>

- **研究論文** — 私たちのラボからの 5 論文（[AI-Researcher](https://github.com/HKUDS/AI-Researcher)、[LightRAG](https://github.com/HKUDS/LightRAG) など）
- **データサイエンス教科書** — 8 章、296 ページ（[書籍リンク](https://ma-lab-berkeley.github.io/deep-representation-learning-book/)）

</details>

1. [Google Drive](https://drive.google.com/drive/folders/1iWwfZXiTuQKQqUYb5fGDZjLCeTUP6DA6?usp=sharing) からダウンロード
2. `data/` ディレクトリに解凍

> デモ KB は `text-embedding-3-large` を使用し、`dimensions = 3072`

**⑤ 独自のナレッジベースを作成** *(起動後)*

1. http://localhost:3782/knowledge にアクセス
2. 「New Knowledge Base」をクリック → 名前を入力 → PDF/TXT/MD ファイルをアップロード
3. ターミナルで進捗を監視

---

### ステップ 2: インストール方法を選択

<table>
<tr>
<td width="50%" valign="top">

<h3 align="center">🐳 Docker デプロイ</h3>
<p align="center"><b>推奨</b> — Python/Node.js 設定不要</p>

---

**前提条件**：[Docker](https://docs.docker.com/get-docker/) と [Docker Compose](https://docs.docker.com/compose/install/)

<details open>
<summary><b>🚀 オプション A: 事前構築済みイメージ（最速）</b></summary>

```bash
# 事前構築済みイメージをプルして実行（約30秒）
docker run -d --name deeptutor \
  -p 8001:8001 -p 3782:3782 \
  -e LLM_MODEL=gpt-4o \
  -e LLM_API_KEY=your-api-key \
  -e LLM_HOST=https://api.openai.com/v1 \
  -e EMBEDDING_MODEL=text-embedding-3-large \
  -e EMBEDDING_API_KEY=your-api-key \
  -e EMBEDDING_HOST=https://api.openai.com/v1 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config:ro \
  ghcr.io/hkuds/deeptutor:latest
```

または `.env` ファイルを使用：

```bash
docker run -d --name deeptutor \
  -p 8001:8001 -p 3782:3782 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config:ro \
  ghcr.io/hkuds/deeptutor:latest
```

</details>

<details>
<summary><b>🔨 オプション B: ソースコードからビルド</b></summary>

```bash
# ビルドして起動（初回実行は約 5-10 分）
docker compose up --build -d

# ログを表示
docker compose logs -f
```

</details>

**コマンド**：

```bash
docker compose up -d      # 起動
docker compose logs -f    # ログ
docker compose down       # 停止
docker compose up --build # 再ビルド
docker pull ghcr.io/hkuds/deeptutor:latest  # イメージを更新
```

> **開発モード**：`-f docker-compose.dev.yml` を追加

</td>
<td width="50%" valign="top">

<h3 align="center">💻 手動インストール</h3>
<p align="center">開発または非 Docker 環境用</p>

---

**前提条件**：Python 3.10+、Node.js 18+

**環境を設定**：

```bash
# conda を使用（推奨）
conda create -n deeptutor python=3.10
conda activate deeptutor

# または venv を使用
python -m venv venv
source venv/bin/activate
```

**依存関係をインストール**：

```bash
bash scripts/install_all.sh

# または手動：
pip install -r requirements.txt
npm install --prefix web
```

**起動**：

```bash
# Web インターフェースを起動
python scripts/start_web.py

# または CLI のみ
python scripts/start.py

# 停止：Ctrl+C
```

</td>
</tr>
</table>

### アクセス URL

| サービス | URL | 説明 |
|:---:|:---|:---|
| **フロントエンド** | http://localhost:3782 | メイン Web インターフェース |
| **API ドキュメント** | http://localhost:8001/docs | インタラクティブ API ドキュメント |

---

## 📄 ライセンス

このプロジェクトは **[AGPL-3.0 ライセンス](LICENSE)** でライセンスされています。


## ⭐ Star History

<div align="center">
<a href="https://star-history.com/#HKUDS/DeepTutor&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=HKUDS/DeepTutor&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=HKUDS/DeepTutor&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=HKUDS/DeepTutor&type=Date" />
 </picture>
</a>
</div>


## 🤝 貢献

コミュニティからの貢献を歓迎します！コード品質と一貫性を確保するため、以下のガイドラインに従ってください。

<details>
<summary><b>開発セットアップ</b></summary>

### Pre-commit Hooks セットアップ

このプロジェクトは **pre-commit hooks** を使用して、コミット前に自動的にコードをフォーマットし、問題をチェックします。

**ステップ 1: pre-commit をインストール**
```bash
# pip を使用
pip install pre-commit

# または conda を使用
conda install -c conda-forge pre-commit
```

**ステップ 2: Git hooks をインストール**
```bash
cd DeepTutor
pre-commit install
```

**ステップ 3: （オプション）すべてのファイルでチェックを実行**
```bash
pre-commit run --all-files
```

`git commit` を実行するたびに、pre-commit hooks は自動的に以下を行います：
- Ruff で Python コードをフォーマット
- Prettier でフロントエンドコードをフォーマット
- 構文エラーをチェック
- YAML/JSON ファイルを検証
- 潜在的なセキュリティ問題を検出

### コード品質ツール

| ツール | 目的 | 構成 |
|:---:|:---|:---:|
| **Ruff** | Python コード確認とフォーマット | `pyproject.toml` |
| **Prettier** | フロントエンドコード形式 | `web/.prettierrc.json` |
| **detect-secrets** | セキュリティチェック | `.secrets.baseline` |

> **注意**: プロジェクトはフォーマット競合を回避するため、Black の代わりに **Ruff format** を使用します。

### よく使うコマンド

```bash
# 通常のコミット（hooks が自動実行）
git commit -m "コミットメッセージ"

# すべてのファイルを手動でチェック
pre-commit run --all-files

# hooks を最新バージョンに更新
pre-commit autoupdate

# hooks をスキップ（推奨されません。緊急時のみ）
git commit --no-verify -m "緊急修正"
```

</details>

### 貢献ガイドライン

1. **Fork とクローン**: リポジトリを Fork してクローン
2. **ブランチを作成**: `main` からフィーチャーブランチを作成
3. **Pre-commit をインストール**: 上記セットアップステップに従う
4. **変更を実施**: プロジェクトのスタイルに従ってコードを記述
5. **テスト**: 変更が正しく機能することを確認
6. **コミット**: Pre-commit hooks が自動的にコードをフォーマット
7. **プッシュと PR**: Fork にプッシュして Pull Request を作成

### 問題を報告

- GitHub Issues を使用してバグを報告またはフィーチャーを提案
- 問題に関する詳細情報を提供
- バグの場合は、再現手順を含める

<div align="center">
<br>
❤️ すべての貢献者の貴重な貢献に感謝します。

</div>

## 🔗 関連プロジェクト

<div align="center">

| [⚡ LightRAG](https://github.com/HKUDS/LightRAG) | [🎨 RAG-Anything](https://github.com/HKUDS/RAG-Anything) | [💻 DeepCode](https://github.com/HKUDS/DeepCode) | [🔬 AI-Researcher](https://github.com/HKUDS/AI-Researcher) |
|:---:|:---:|:---:|:---:|
| シンプルで高速の RAG | マルチモーダル RAG | AI コードアシスタント | 研究自動化 |

**[香港大学データインテリジェンスラボ](https://github.com/HKUDS)**

[⭐ Star us](https://github.com/HKUDS/DeepTutor/stargazers) · [🐛 Report a bug](https://github.com/HKUDS/DeepTutor/issues) · [💬 Discussions](https://github.com/HKUDS/DeepTutor/discussions)

---
*✨ **DeepTutor** のご利用ありがとうございます！*

<img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.DeepTutor&style=for-the-badge&color=00d4ff" alt="Views">

</div>
