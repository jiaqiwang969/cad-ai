# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 **TraceParts 网站爬虫系统** - 模块化的生产级爬虫，用于从 TraceParts 网站提取产品分类、产品链接和规格信息。系统采用先进的反检测技术，包含验证码识别功能。

## 常用命令

### 主要流水线命令
- `make pipeline` - 运行主要的 V2 流水线（32 并发，渐进式缓存）
- `make install` - 安装所有依赖包括 Playwright 浏览器
- `make verify` - 快速 API 连接测试
- `make check` - 检查依赖安装状态
- `make clean` - 清理临时文件

### 测试和开发
- `python run_pipeline_v2.py` - 直接执行流水线，支持自定义参数
- `test/` 目录中的独立测试文件（01-13 系列）
- `test/10-test_product_cad_download.py` - CAD 文件下载功能

### 环境配置
- 必需环境变量：`OPENAI_API_KEY`、`OPENAI_BASE_URL`
- 可选：`TRACEPARTS_EMAIL`、`TRACEPARTS_PASSWORD`（用于 CAD 下载）
- TraceParts 凭据已在 Makefile 中预配置用于基础爬取

## 代码架构

### 核心组件
- **src/pipelines/**: 主要执行流水线，缓存管理
- **src/crawler/**: 模块化爬虫（分类、产品、规格）
- **src/utils/**: 浏览器管理、反检测、验证码识别、网络处理
- **config/**: 集中化设置和日志配置

### 关键类
- `CacheManager` (src/pipelines/cache_manager.py) - 渐进式三级缓存系统
- `OptimizedFullPipelineV2` (src/pipelines/optimized_full_pipeline_v2.py) - 主流水线
- `BrowserManager` (src/utils/browser_manager.py) - Selenium/Playwright 浏览器池
- `Settings` (config/settings.py) - 全局配置管理

### 数据流程
1. **分类树**: 提取产品分类并构建层级结构
2. **产品链接**: 从叶子分类批量提取产品 URL
3. **规格信息**: 提取详细的产品规格和参数

### 反检测特性
- 隐身浏览器配置
- User-Agent 轮换
- 智能延迟和随机化
- 网络故障检测和自动暂停
- 会话管理和 Cookie 处理

## 配置

### 配置文件位置
- 全局配置：`config/settings.py` (Settings 类)
- API 配置：`config.py` (OpenAI API 设置)
- 运行时配置：环境变量和命令行参数

### 主要配置区域
- **CRAWLER**: 工作线程数、超时时间、浏览器设置
- **NETWORK**: 失败阈值、暂停逻辑、重试策略
- **STORAGE**: 缓存 TTL、输出目录、数据库路径
- **AUTH**: TraceParts 凭据、会话管理
- **CAPTCHA**: GPT-4o 集成用于 OCR 识别

### 性能调优
- 默认：32 个工作线程实现最佳性能
- 浏览器池大小与工作线程数匹配
- 渐进式缓存减少冗余工作
- 网络监控防止被检测

## 输出结构

### 主要输出
- `results/products/`: 包含完整产品数据的最终 JSON 结果
- `results/cache/`: 渐进式缓存文件（分类、产品、规格）
- `results/logs/`: 带时间戳的执行日志

### 缓存系统
- **级别 1**: 分类树（24小时 TTL）
- **级别 2**: 每个分类的产品链接（24小时 TTL）
- **级别 3**: 产品规格（24小时 TTL）

## 开发注意事项

### 浏览器管理
- 支持 Selenium 和 Playwright
- Selenium 使用 undetected-chromedriver
- 浏览器实例池化和重用
- 自动清理和错误恢复

### 错误处理
- 按错误类型分层重试策略
- 网络故障检测和自动暂停
- 详细日志记录用于调试
- 验证码失败时优雅降级

### 添加新功能
- 遵循 `src/crawler/` 中的模块化模式
- 使用 `ThreadSafeLogger` 进行日志记录
- 与 `CacheManager` 集成实现持久化
- 在 `Settings` 类中添加配置

### 测试环境
- 使用 `scripts/` 生成测试数据
- `test/legacy/` 中的历史测试文件作为参考
- 当前测试套件：`test/01-13` 系列