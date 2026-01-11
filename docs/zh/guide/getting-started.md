# 快速开始

5 分钟内让 DeepTutor 运行起来。

## 环境要求

- Python 3.10+
- Node.js 18+
- 一个 LLM API 密钥（OpenAI、Anthropic、DeepSeek 等）

## 安装

::: code-group

```bash [快速安装]
# 克隆并设置
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# 配置 API 密钥
cp .env.example .env
# 编辑 .env 填入你的 API 密钥

# 安装并启动
bash scripts/install_all.sh
python scripts/start_web.py
```

```bash [Docker]
docker run -d --name deeptutor \
  -p 8001:8001 -p 3782:3782 \
  -e LLM_MODEL=gpt-4o \
  -e LLM_API_KEY=your-key \
  -e LLM_HOST=https://api.openai.com/v1 \
  -e EMBEDDING_MODEL=text-embedding-3-large \
  -e EMBEDDING_API_KEY=your-key \
  -e EMBEDDING_HOST=https://api.openai.com/v1 \
  ghcr.io/hkuds/deeptutor:latest
```

:::

## `.env` 核心变量

```bash
# 必需
LLM_MODEL=gpt-4o
LLM_API_KEY=your_api_key
LLM_HOST=https://api.openai.com/v1

EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_API_KEY=your_api_key
EMBEDDING_HOST=https://api.openai.com/v1
```

> 📖 **完整配置选项**: 参见 [配置说明](/zh/guide/configuration) 或 [README](https://github.com/HKUDS/DeepTutor#step-1-pre-configuration)

## 访问地址

| 服务 | 地址 |
|:--------|:----|
| **Web 应用** | http://localhost:3782 |
| **API 文档** | http://localhost:8001/docs |

## 创建第一个知识库

1. 访问 http://localhost:3782/knowledge
2. 点击 **"新建知识库"**
3. 上传 PDF、TXT 或 Markdown 文件
4. 等待处理完成

完成！现在可以开始使用 **智能解题**、**题目生成** 或 **深度研究** 等模块。

## 下一步

- [配置说明 →](/zh/guide/configuration)
- [常见问题 →](/zh/guide/troubleshooting)
- [完整安装指南 →](https://github.com/HKUDS/DeepTutor#-getting-started)
