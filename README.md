# TraceParts CAD Scraper – OpenAI & LangChain Demo 项目

> 通过 **OpenAI GPT-4o** 与 **LangChain** 驱动的智能化爬虫，自动获取 [TraceParts](https://www.traceparts.com/) 产品类目并完成 CAD 模型下载。
>
> 项目着重演示以下能力：
>
> 1. OpenAI / LangChain 接入最佳实践
> 2. 多层级分类树递归爬取 & 高并发抓取
> 3. Playwright + Stealth 规避检测
> 4. **验证码自动识别**（支持 GPT-4o / TrOCR / pytesseract）
> 5. 完整下载链路：登录 → 触发下载 → 处理压缩包 → 数据持久化

---

## 目录结构

```text
50-爬虫01/
├── README.md                      # 项目说明（本文档）
├── Makefile                       # 一键安装 / 测试 / 工具命令
├── requirements.txt               # Python 依赖
├── config.py                      # 配置项（API、浏览器、日志等）
├── utils/                         # 通用工具（验证码识别等）
│   └── captcha_solver.py          # CaptchaSolver – 返回 **原始 OCR 文本**
├── test/                          # 测试脚本（01-10）
│   └── intermediate/              # 深度调研脚本（11+），默认不会随 Makefile 执行
└── results/                       # 运行产物（JSON / 截图 / 调试图等）
```

### 关于 CaptchaSolver

`utils/captcha_solver.py` **不会对 OCR 结果做任何大小写或长度裁剪**，始终返回模型识别到的原始文本。
如果需要清洗，可以在业务侧自行调用 `str.upper()`、正则截取等方式处理。

---

## 快速上手

1. 克隆仓库并进入目录

   ```bash
   git clone <repo-url>
   cd 50-爬虫01
   ```

2. 配置环境变量（可选）

   ```bash
   cp .env.example .env  # 按需修改
   export $(grep -v '^#' .env | xargs)
   ```

3. 安装依赖并拉取浏览器内核

   ```bash
   make install
   ```

4. 运行测试

   ```bash
   # 运行全部（01-10）
   make test

   # 只跑分类树递归爬取（06）
   make test-06
   ```

> **提示**：如需体验更高级的脚本（验证码规避、真实浏览器、下载诊断等），请进入 `test/intermediate/` 手动执行相应文件。

---

## 测试用例一览

| 编号 | 脚本 | 说明 |
|------|----------------------------------|-------------------------------------------------------------|
| 01 | `01-test_openai_api.py` | OpenAI Python SDK 连通性 & 计费验证 |
| 02 | `02-test_langchain_api.py` | LangChain Chat & Chain 基础能力 |
| 03 | `03-test_langchain_web_scraping.py` | 智能网页块分析 + 聚焦提取 |
| 04 | `04-test_async_web_scraping.py` | **异步并发** 多页面采集，对比性能 |
| 05 | `05-test_category_drill_down.py` | 类目深度递归，获取全部子分类链接 |
| 06 | `06-test_classification_tree_recursive.py` | 构建 TraceParts **完整分类树**（递归版） |
| 07 | `07-test_classification_tree_nested.py` | 构建嵌套树（一次性提取并重组） |
| 08 | `08-test_leaf_product_links.py` | 抽取叶节点产品链接 |
| 09 | `09-test_batch_leaf_product_links.py` | 批量叶节点抓取 & 结果归并 |
| **10** | `10-test_product_cad_download.py` | 🏁 **整合演示**：登录 + 验证码识别 + CAD 下载 |

> 旧的 11-13 号实验脚本已迁移至 `test/intermediate/`，默认不会随 `make test` 执行，但仍可参考。

---

## 常用命令（Makefile）

| 命令 | 描述 |
|------|------|
| `make install` | 安装依赖 + Playwright Chromium |
| `make test` | 顺序执行 01-10 全套测试 |
| `make test-0X` | 只运行指定编号脚本，例如 `make test-04` |
| `make check` | 检查关键依赖版本 |
| `make list` | 列出 `test/` 目录脚本 |
| `make results` | 列出 `results/` 生成文件 |
| `make clean` | 移除临时 / 结果文件 |
| `make help` | 查看全部命令 |

---

## 环境依赖

- Python 3.9+
- 网络可访问 OpenAI 代理 (`https://ai.pumpkinai.online/v1`) 及 TraceParts 网站
- 完整依赖见 `requirements.txt`，关键包：
  - openai, langchain, playwright, undetected-chromedriver
  - opencv-python, pillow, pytesseract, transformers, torch

---

## 常见问题

1. **安装失败 / 权限不足** – 追加 `--break-system-packages` 或使用虚拟环境。
2. **API 429 / 401** – 检查代理地址、Key 是否正确，或线路被墙。
3. **验证码识别不准** – 开启 `debug=True`，查看 `results/captcha_debug/` 中间产物；尝试 `ocr_method="trocr"` 或 `"pytesseract"`。
4. **TraceParts 拒绝访问** – 适当延迟请求、切换 IP 或使用真实浏览器模式。

---

## License

MIT © 2025 now 