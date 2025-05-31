# OpenAI API 爬虫测试项目

## 项目概述

本项目用于验证 OpenAI API 代理服务的连接性和功能性，包括原生 OpenAI API、LangChain 框架测试和智能网页爬取功能。

## 项目结构

```
50-爬虫01/
├── README.md                           # 项目说明文档
├── Makefile                            # 自动化构建和测试脚本
├── requirements.txt                    # Python依赖包列表
├── test/                               # 测试目录
│   ├── 01-test_openai_api.py          # OpenAI API 原生测试
│   ├── 02-test_langchain_api.py       # LangChain API 测试
│   └── 03-test_langchain_web_scraping.py # LangChain 网页爬取测试
└── results/                            # 爬取结果目录
    └── traceparts_categories.json      # TraceParts类目数据
```

## API 配置

本项目使用环境变量管理API密钥，确保安全性。

### 配置步骤

1. 复制环境变量模板文件：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，填入您的实际API配置：
   ```bash
   OPENAI_API_KEY=your-actual-api-key-here
   OPENAI_BASE_URL=https://ai.pumpkinai.online/v1
   OPENAI_MODEL=gpt-4o-mini
   ```

3. 确保 `.env` 文件已被 `.gitignore` 排除，不会提交到Git

### 默认配置

- **Base URL**: `https://ai.pumpkinai.online/v1`
- **Model**: `gpt-4o-mini`
- **Temperature**: `0.7`
- **Max Tokens**: `200`

## 快速开始

### 1. 安装依赖

```bash
make install
```

### 2. 运行所有测试

```bash
make test
```

### 3. 只运行网页爬取测试

```bash
make test-03
```

### 4. 查看爬取结果

```bash
make results
```

### 5. 查看帮助

```bash
make help
```

## 可用命令

| 命令 | 说明 |
|------|------|
| `make install` | 安装项目依赖包 |
| `make test` | 运行所有测试 |
| `make test-openai` | 只运行 OpenAI API 测试 |
| `make test-langchain` | 只运行 LangChain 测试 |
| `make test-scraping` | 只运行网页爬取测试 |
| `make test-01` | 运行测试 01 (OpenAI API) |
| `make test-02` | 运行测试 02 (LangChain) |
| `make test-03` | 运行测试 03 (网页爬取) |
| `make verify` | 快速验证 API 连接 |
| `make check` | 检查依赖包状态 |
| `make list` | 列出测试文件 |
| `make results` | 查看爬取结果文件 |
| `make clean` | 清理临时文件 |
| `make help` | 显示帮助信息 |

## 测试说明

### 01-test_openai_api.py
- 验证原生 OpenAI Python SDK 的连接性
- 测试直接配置方式和环境变量方式
- 检查 API 响应和 token 使用情况

### 02-test_langchain_api.py
- 验证 LangChain 框架与 OpenAI API 的集成
- 测试基本对话、Chain 功能、环境变量配置
- 验证流式响应功能

### 03-test_langchain_web_scraping.py
- **智能网页爬取功能** 🆕
- 目标网站：`https://www.traceparts.cn/en`
- 使用 LangChain + OpenAI 智能提取模型类目信息
- 自动过滤无关内容（新闻、介绍、营销信息等）
- 双重提取方法：块分析 + 聚焦提取
- 结果保存为结构化 JSON 文件

#### 爬取功能特点：
- 🤖 **AI 驱动**：使用 GPT-4o-mini 智能识别和提取相关内容
- 🎯 **精准过滤**：只提取模型类目、产品分类等核心信息
- 📊 **结构化输出**：生成标准 JSON 格式的数据文件
- 🔄 **多重验证**：采用两种不同方法交叉验证提取结果
- 💾 **数据持久化**：自动保存到 `results/` 目录

## 爬取结果示例

运行网页爬取测试后，会在 `results/` 目录生成 JSON 文件：

```json
{
  "extraction_method_1": {
    "main_categories": [
      {
        "name": "机械零件",
        "description": "包含轴承、齿轮、紧固件等",
        "subcategories": [...]
      }
    ]
  },
  "extraction_method_2": {
    "product_categories": [
      {
        "category_name": "标准件",
        "category_type": "机械零件",
        "description": "螺钉、螺母、垫片等标准化零件",
        "subcategories": [...]
      }
    ]
  },
  "metadata": {
    "url": "https://www.traceparts.cn/en",
    "extraction_date": "2025-01-30T...",
    "content_length": 15420,
    "chunks_count": 8
  }
}
```

## 环境要求

- Python 3.7+
- 网络连接（访问 OpenAI API 代理服务 + 目标网站）
- 依赖包：
  - `openai>=1.0.0`
  - `langchain>=0.1.0`
  - `langchain-openai>=0.1.0`
  - `langchain-community>=0.0.10`
  - `beautifulsoup4>=4.12.0`
  - `requests>=2.28.0`
  - `lxml>=4.9.0`

## 故障排除

1. **依赖安装失败**：尝试使用 `--break-system-packages` 标志
2. **API 连接失败**：检查网络连接和 API 密钥
3. **网页爬取失败**：检查目标网站连接和内容格式
4. **JSON 解析错误**：AI 可能返回非标准格式，程序会自动处理
5. **测试运行失败**：确保所有依赖包已正确安装

## 开发说明

- 测试文件按编号顺序命名 (`01-`, `02-`, `03-`, ...)
- 每个测试都包含详细的错误处理和输出格式化
- 支持多种测试方式（直接配置、环境变量等）
- 网页爬取使用智能内容识别，避免提取无关信息
- 结果文件自动按时间戳命名，避免覆盖 