# TraceParts 爬虫架构文档

## 项目概述

TraceParts 爬虫是一个模块化、可扩展的网页爬虫系统，专门用于从 TraceParts 网站爬取产品分类、产品链接和产品规格信息。

## 架构设计

### 1. 目录结构

```
50-爬虫01/
├── src/                      # 核心源代码
│   ├── crawler/             # 爬虫模块
│   │   ├── classification.py    # 分类树爬取
│   │   ├── products.py         # 产品链接爬取
│   │   └── specifications.py   # 规格信息爬取
│   ├── auth/                # 认证模块
│   ├── utils/               # 工具模块
│   │   ├── browser_manager.py  # 浏览器管理
│   │   ├── captcha_solver.py   # 验证码处理
│   │   └── net_guard.py        # 网络监控
│   └── pipelines/           # 流水线
│       └── full_pipeline.py    # 完整流水线
├── config/                  # 配置
│   ├── settings.py         # 全局设置
│   └── logging_config.py   # 日志配置
├── tests/                   # 测试
├── docs/                    # 文档
└── scripts/                 # 脚本工具
```

### 2. 核心模块

#### 2.1 爬虫模块 (src/crawler/)

- **ClassificationCrawler**: 负责爬取产品分类树
  - 提取分类链接
  - 构建层级结构
  - 识别叶节点

- **ProductLinksCrawler**: 负责从叶节点提取产品链接
  - 处理分页
  - 批量爬取
  - 重试机制

- **SpecificationsCrawler**: 负责提取产品规格
  - 解析产品页面
  - 提取规格表格
  - 数据验证

#### 2.2 工具模块 (src/utils/)

- **BrowserManager**: 统一管理浏览器实例
  - 支持 Selenium 和 Playwright
  - 浏览器池管理
  - 反检测策略

- **NetworkGuard**: 网络异常监控
  - 失败统计
  - 自动暂停
  - 健康检查

- **CaptchaSolver**: 验证码处理
  - GPT-4o OCR
  - 图像处理
  - 重试逻辑

#### 2.3 配置管理 (config/)

- **Settings**: 集中管理所有配置
  - 爬虫参数
  - 网络设置
  - 存储路径
  - 重试策略

- **LoggingConfig**: 日志配置
  - 格式化
  - 文件轮转
  - 日志级别

### 3. 数据流

```
分类根页面
    ↓
ClassificationCrawler (提取分类链接)
    ↓
构建分类树，识别叶节点
    ↓
ProductLinksCrawler (批量爬取产品链接)
    ↓
SpecificationsCrawler (批量爬取产品规格)
    ↓
保存JSON结果
```

### 4. 并发策略

- 使用 ThreadPoolExecutor 实现并发
- 动态调整并发数
- 基于成功率的自适应策略
- 批次处理避免内存溢出

### 5. 错误处理

- 分级重试策略
- 网络异常自动暂停
- 详细的错误日志
- 失败任务记录

### 6. 性能优化

- 浏览器实例复用
- 缓存机制（24小时）
- 批量处理
- 智能滚动加载

## 使用指南

### 基本使用

```bash
# 运行完整流水线
make pipeline

# 快速模式（32并发）
make pipeline-fast

# 禁用缓存
make pipeline-nocache
```

### 命令行参数

```bash
python run_pipeline.py --help

参数说明：
  --workers N        设置并发数（默认16）
  --output FILE      输出文件路径
  --no-cache         禁用缓存
  --browser TYPE     浏览器类型 (selenium/playwright)
```

### 配置调整

编辑 `config/settings.py` 修改：
- 并发数限制
- 超时时间
- 重试次数
- 网络阈值

## 扩展开发

### 添加新的爬虫

1. 在 `src/crawler/` 创建新模块
2. 继承 `LoggerMixin` 获取日志功能
3. 使用 `BrowserManager` 管理浏览器
4. 集成到流水线中

### 添加新的工具

1. 在 `src/utils/` 创建新模块
2. 遵循现有的接口规范
3. 添加单元测试

## 部署建议

### Docker 部署

```dockerfile
FROM python:3.9-slim

# 安装 Chrome
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver

# 复制代码
COPY . /app
WORKDIR /app

# 安装依赖
RUN pip install -r requirements.txt

# 运行
CMD ["python", "run_pipeline.py"]
```

### 监控建议

- 使用 Prometheus 收集指标
- Grafana 可视化展示
- 设置告警规则

## 故障排查

### 常见问题

1. **浏览器启动失败**
   - 检查 Chrome/Chromium 安装
   - 确认驱动版本匹配

2. **网络频繁暂停**
   - 调整 `NETWORK` 配置中的阈值
   - 检查目标网站状态

3. **内存占用过高**
   - 减少并发数
   - 启用批次处理

### 调试技巧

- 设置环境变量 `LOG_LEVEL=DEBUG`
- 查看 `results/logs/` 中的日志
- 使用 `--workers 1` 单线程调试 