# TraceParts 爬虫系统 v2.0

## 项目概述

**模块化爬虫架构**：全新重构的 TraceParts 爬虫系统，采用模块化设计，支持产品分类、产品链接、产品规格的完整爬取流程。

🚀 **新架构特性**：
- 模块化设计，易于扩展和维护
- 统一的配置管理
- 智能的并发控制
- 完善的错误处理和重试机制
- 网络异常自动暂停和恢复

🎯 **快速开始**：`make pipeline` 即可运行完整爬取流程。

## 核心功能

### 爬虫功能
- 🌳 **分类树爬取**：完整提取 TraceParts 产品分类结构
- 📦 **产品链接提取**：从叶节点批量提取产品链接
- 📋 **规格信息爬取**：提取产品详细规格参数
- 🔄 **批量并发处理**：支持多线程并发爬取

### 系统特性
- 🏗️ **模块化架构**：清晰的模块划分，易于维护
- ⚡ **高性能**：浏览器池、并发控制、缓存机制
- 🛡️ **稳定可靠**：智能重试、网络监控、错误恢复
- 📊 **数据管理**：结构化JSON输出，支持增量更新

### 扩展功能
- 🥷 **反检测技术**：绕过自动化检测
- 🤖 **验证码处理**：集成 GPT-4o OCR 识别
- 💾 **CAD 文件下载**：支持多种格式下载（通过 test-10）

## 快速开始

### 1. 安装依赖
```bash
make install
```

### 2. 运行完整爬虫流程

#### 标准版本
```bash
# 标准模式（16并发）
make pipeline

# 快速模式（32并发）
make pipeline-fast

# 禁用缓存模式
make pipeline-nocache
```

#### 优化版本（推荐 - 性能提升10-20倍）
```bash
# 优化版标准模式（32并发）
make pipeline-optimized

# 优化版最大性能（64并发）
make pipeline-optimized-max

# 优化版禁用缓存
make pipeline-optimized-nocache
```

⚡ **优化版特点**：
- 去除双重页面加载（100%性能提升）
- 预编译所有配置常量（5-15%性能提升）
- 简化日志和浏览器管理（30-50%性能提升）
- 优化JavaScript和按钮选择器（10-20%性能提升）
- 详见 [优化版Pipeline使用指南](docs/optimized_pipeline_guide.md)

### 3. 自定义运行
```bash
# 指定并发数
python run_pipeline.py --workers 8

# 指定输出文件
python run_pipeline.py --output results/my_data.json

# 使用 Playwright（需要先安装）
python run_pipeline.py --browser playwright
```

### 4. CAD 文件下载（旧功能）
```bash
# 需要配置账号
export TRACEPARTS_EMAIL=your@email.com
export TRACEPARTS_PASSWORD=yourpassword

# 运行 CAD 下载
make test-10
```

## 项目结构

### 新架构（v2.0）
```
50-爬虫01/
├── src/                          # 核心源代码
│   ├── crawler/                 # 爬虫模块
│   │   ├── classification.py   # 分类树爬取
│   │   ├── products.py        # 产品链接爬取
│   │   └── specifications.py  # 规格信息爬取
│   ├── utils/                  # 工具模块
│   │   ├── browser_manager.py # 浏览器管理
│   │   ├── captcha_solver.py  # 验证码处理
│   │   └── net_guard.py       # 网络监控
│   └── pipelines/             # 流水线
│       └── full_pipeline.py   # 完整流水线
├── config/                     # 配置管理
│   ├── settings.py            # 全局设置
│   └── logging_config.py      # 日志配置
├── run_pipeline.py            # 主入口脚本
└── docs/                      # 项目文档
    └── architecture.md        # 架构说明
```

### 旧版本文件（保留兼容）
```
├── test/                       # 原测试脚本
│   ├── 01-09-*.py            # 功能测试脚本
│   ├── 10-*.py               # CAD下载脚本
│   └── legacy/               # 历史版本
├── traceparts_full_pipeline.py # 原完整流水线
└── utils/                     # 原工具模块
```

## 工作原理

1. **隐身登录**：使用高级反检测技术登录 TraceParts
2. **页面导航**：自动跳转到指定产品页面
3. **格式选择**：智能选择最优 CAD 文件格式
4. **验证码识别**：GPT-4o 实时 OCR 识别并填写
5. **触发下载**：模拟用户点击操作启动下载
6. **文件保存**：监听下载事件，自动保存到本地

## 技术架构

### 核心组件

- **Playwright + playwright-stealth**：隐身浏览器自动化
- **GPT-4o Vision API**：验证码图像识别
- **OpenCV + Pillow**：图像处理与验证码区域定位
- **动态模块加载**：灵活复用 legacy 代码组件

### 验证码识别流程

```
页面截图 → 刷新图标定位 → 验证码区域裁剪 → GPT-4o OCR → 结果填写
     ↓
如识别错误 → 重新OCR（告知上次错误） → 重试填写 → 重新下载
```

## 可用命令

### 新架构命令（推荐）
| 命令 | 说明 |
|------|------|
| `make pipeline` | 🚀 **运行新架构流水线（标准模式）** |
| `make pipeline-fast` | ⚡ 快速模式（32并发） |
| `make pipeline-nocache` | 🔄 禁用缓存运行 |

### 优化版命令（终极性能）
| 命令 | 说明 |
|------|------|
| `make pipeline-optimized` | 🚀 **优化版流水线（性能提升10-20倍）** |
| `make pipeline-optimized-max` | ⚡ 最大性能模式（64并发） |
| `make pipeline-optimized-nocache` | 🔄 优化版禁用缓存运行 |

### 传统命令（兼容保留）
| 命令 | 说明 |
|------|------|
| `make test-11` | 运行原版全链条抓取 |
| `make test-10` | 🎯 运行 CAD 文件下载 |
| `make test-01` ~ `make test-09` | 各项功能测试 |

### 系统命令
| 命令 | 说明 |
|------|------|
| `make install` | 安装项目依赖包 |
| `make verify` | 快速验证 API 连接 |
| `make check` | 检查依赖包状态 |
| `make list` | 列出测试文件 |
| `make results` | 查看结果文件 |
| `make clean` | 清理临时文件 |
| `make help` | 显示帮助信息 |

## 新架构特性

### 模块化设计
- **分离关注点**：爬虫逻辑、工具函数、配置管理完全分离
- **易于扩展**：添加新功能只需创建新模块
- **代码复用**：通过浏览器管理器等共享组件提高复用性

### 性能优化
- **浏览器池**：复用浏览器实例，减少启动开销
- **智能并发**：根据成功率动态调整并发数
- **批量处理**：分批处理大量数据，避免内存溢出
- **缓存机制**：24小时缓存分类树，避免重复爬取

### 稳定性保障
- **网络监控**：自动检测网络异常并暂停
- **分级重试**：不同错误类型采用不同重试策略
- **错误恢复**：详细记录失败任务，支持断点续爬
- **日志追踪**：完整的日志记录，便于问题排查

## 配置选项

### 全局配置（config/settings.py）

```python
# 爬虫配置
CRAWLER = {
    'max_workers': 16,          # 最大并发数
    'timeout': 60,              # 页面超时时间
    'page_load_timeout': 90,    # 页面加载超时
    'retry_times': 3,           # 默认重试次数
}

# 网络配置
NETWORK = {
    'fail_window_sec': 180,     # 失败统计窗口（3分钟）
    'fail_threshold': 5,        # 失败阈值
    'pause_seconds': 120,       # 暂停时长
}

# 存储配置
STORAGE = {
    'cache_ttl': 86400,         # 缓存有效期（24小时）
    'download_dir': 'results/downloads',
    'products_dir': 'results/products',
}
```

### 环境变量

```bash
# 基础配置
MAX_WORKERS=32                  # 覆盖默认并发数
LOG_LEVEL=DEBUG                 # 日志级别

# TraceParts 账号（CAD下载需要）
TRACEPARTS_EMAIL=your@email.com
TRACEPARTS_PASSWORD=yourpassword

# API 配置（验证码识别）
GPT4O_API_KEY=sk-...
GPT4O_BASE_URL=https://ai.pumpkinai.online/v1
```

## 运行示例

### 新架构运行输出

```bash
$ make pipeline
🚀 运行新架构流水线...
2024-01-20 10:15:30 [INFO] [src.pipelines.full_pipeline] 🚀 开始运行完整爬取流水线
============================================================
2024-01-20 10:15:30 [INFO] [src.pipelines.full_pipeline] 📋 第一步：爬取分类树
============================================================
2024-01-20 10:15:31 [INFO] [src.crawler.classification] 🌐 打开分类根页面: https://www.traceparts.cn/...
2024-01-20 10:15:45 [INFO] [src.crawler.classification] 🔗 提取到 1532 个分类链接
2024-01-20 10:15:46 [INFO] [src.crawler.classification] 🌳 构建分类树完成，共 1414 个叶节点
============================================================
2024-01-20 10:15:46 [INFO] [src.pipelines.full_pipeline] 📦 第二步：爬取产品链接
============================================================
2024-01-20 10:15:46 [INFO] [src.pipelines.full_pipeline] 处理叶节点批次 1/29
2024-01-20 10:16:30 [INFO] [src.crawler.products] ✅ 叶节点 TP01001001 (Bearings) 产品数: 156
2024-01-20 10:16:35 [INFO] [src.crawler.products] ✅ 叶节点 TP01001002 (Bushings) 产品数: 89
...
2024-01-20 10:45:20 [INFO] [src.pipelines.full_pipeline] 当前累计产品链接数: 15632
============================================================
2024-01-20 10:45:21 [INFO] [src.pipelines.full_pipeline] 📊 第三步：爬取产品规格
============================================================
2024-01-20 10:45:21 [INFO] [src.pipelines.full_pipeline] 处理叶节点 TP01001001 的 156 个产品
2024-01-20 10:45:45 [INFO] [src.crawler.specifications] ✅ [1/156] 提取成功: 12 个规格
...
============================================================
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline] 📊 爬取汇总
============================================================
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline] ⏱️  总耗时: 76.7 分钟
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline] 🌳 叶节点: 1414 个
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline] 📦 产品数: 15632 个
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline] 📋 规格数: 186543 个
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline] ✅ 成功率: 1398/1414 叶节点
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline] 🌐 网络统计:
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline]    - 成功请求: 17046
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline]    - 失败请求: 234
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline]    - 成功率: 98.6%
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline]    - 暂停次数: 2
2024-01-20 11:32:15 [INFO] [src.pipelines.full_pipeline] ✅ 结果已保存到: /Users/xxx/results/products/full_pipeline_1705721535.json
```

## 依赖包

精简版核心依赖：

```
# Web 自动化
playwright>=1.44.0
playwright-stealth>=1.0.6

# HTTP 请求 (GPT-4o API)  
requests>=2.28.0

# 图像处理与 OCR
opencv-python>=4.8.0
pillow>=10.0.0
numpy>=1.21.0

# 机器学习 (备用 TrOCR 支持)
transformers>=4.20.0
torch>=1.12.0
```

## 故障排除

### 常见问题

1. **登录失败**
   - 检查账号密码是否正确
   - 确认网络可以访问 TraceParts

2. **验证码识别失败**
   - 检查 GPT-4o API 配置
   - 查看 `results/captcha_debug/` 目录下的调试图片

3. **下载失败**
   - 确认产品 URL 有效
   - 检查 `results/downloads/` 目录权限

4. **浏览器检测**
   - 脚本已集成高级反检测，如仍被检测可查看 legacy 脚本调优

### 调试模式

编辑 `test/10-test_product_cad_download.py`，设置：
```python
solver = CaptchaSolver(debug=True, ocr_method="gpt4o")
```

## 升级说明

### 从旧版本升级到 v2.0

1. **代码兼容**：旧版本的所有功能仍然可用
   - `make test-11` 仍可运行原版爬虫
   - `make test-10` 仍可进行 CAD 下载

2. **推荐迁移**：
   - 使用 `make pipeline` 替代 `make test-11`
   - 新架构性能更好，稳定性更高

3. **配置迁移**：
   - 环境变量完全兼容
   - 新增配置项见 `config/settings.py`

4. **数据兼容**：
   - 输出格式保持一致
   - 可直接使用旧版本的结果文件

## 开发历程

本项目经历了从基础爬虫到模块化架构的完整演进：

- **阶段 1**：基础 API 测试和网页爬取（01-09）
- **阶段 2**：登录与隐身浏览技术（11 系列）
- **阶段 3**：验证码识别与处理（12-13 系列）  
- **阶段 4**：GPT-4o 集成与完整自动化（k 系列）
- **阶段 5**：最终整合与优化（test/10）
- **阶段 6**：模块化重构（v2.0）

详细演进过程见 `test/legacy/README.md`。

## 下一步计划

- [ ] 添加 API 接口支持
- [ ] 实现 Web 管理界面
- [ ] 支持分布式部署
- [ ] 添加更多数据源
- [ ] 优化内存使用

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

MIT License 