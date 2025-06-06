# TraceParts 代码清理计划

## 📋 清理目标

只保留与 `make pipeline-v2` 相关的核心代码，删除所有其他入口点和非必要的代码。

## ✅ 需要保留的文件

### 核心入口和配置
- `run_pipeline_v2.py` - 主入口文件
- `requirements.txt` - 依赖包
- `config.py` - 配置文件
- `.env` (如果存在) - 环境变量
- `.gitignore` - Git配置
- `README.md` - 项目说明

### src/ 目录 (核心模块)
**完整保留以下目录:**
- `src/auth/` - 认证模块 (TraceParts登录)
- `src/utils/` - 工具模块 (日志、网络等)

**有选择性保留:**
- `src/pipelines/`
  - ✅ `optimized_full_pipeline_v2.py` - pipeline-v2核心
  - ✅ `cache_manager.py` - 缓存管理器
  - ❌ 删除其他pipeline文件

- `src/crawler/`
  - ✅ `classification_enhanced.py` - 分类树爬取
  - ✅ `ultimate_products_v2.py` - 产品链接爬取
  - ✅ `specifications_*.py` - 规格提取
  - ✅ 其他核心爬虫模块
  - ❌ 删除过时的爬虫版本

### Makefile 
**只保留以下命令:**
- `pipeline-v2` 系列命令
- `cache-*` 系列命令 (缓存管理)
- `install`, `clean`, `verify`, `check`, `help` (基础命令)

### 目录结构
- `results/` - 结果目录 (保留结构，清空内容)
- `config/` - 配置目录
- `docs/` - 相关文档 (选择性保留)

## ❌ 需要删除的文件

### 根目录文件
- `run_pipeline.py` - 老版本pipeline
- `run_optimized_pipeline.py` - 优化版pipeline
- `run_incremental_update.py` - 增量更新
- `run_efficient_update.py` - 高效更新
- `run_cache_manager.py` - 独立缓存管理器
- `run_gui.py` - GUI界面
- `traceparts_full_pipeline.py` - 独立pipeline
- `pipeline_traceparts_allinone.py` - 一体化pipeline
- `extend_cache.py` - 缓存扩展
- `net_guard.py` - 网络守护
- `traceparts_gui.py` - GUI主文件
- `*.png` 图片文件
- 所有 `debug_*.py` 文件
- 所有 `test_*.py` 文件

### test/ 目录
**完全删除整个test目录**
- `01-test_openai_api.py` 到 `10-test_product_cad_download.py`
- 所有测试文件
- `test/legacy/` 目录

### scripts/ 目录
**大部分删除，只保留必要的:**

**保留:**
- 可能保留 1-2 个与 pipeline-v2 直接相关的脚本

**删除:**
- 所有 `test_*.py` 脚本
- 所有 `debug_*.py` 脚本
- 部署和监控脚本 (`deploy_production.sh`, `health_monitor.py` 等)
- 性能测试脚本
- GUI相关脚本
- 演示脚本 (`demo_*.py`)
- 缓存工具脚本 (除非与pipeline-v2直接相关)

### src/pipelines/ 清理
**删除:**
- `full_pipeline.py` - 原始pipeline
- `optimized_full_pipeline.py` - 优化版pipeline
- 其他非V2的pipeline文件

### src/crawler/ 清理
**删除:**
- 过时的爬虫版本
- 测试版本的爬虫
- 非核心功能的爬虫

### Makefile 清理
**删除以下make目标:**
- `test-01` 到 `test-11` 所有测试命令
- `pipeline`, `pipeline-fast`, `pipeline-nocache` (老版本)
- `pipeline-optimized*` 系列 (优化版)
- `update*` 系列 (增量更新)
- `monitor*`, `deploy*` 系列 (监控部署)
- `gui` 相关命令
- 各种调试命令
- 生产环境管理命令

### 其他目录
- `utils/` 目录 (如果与src/utils重复)
- `venv/` 目录 (如果存在，通常不提交)
- `__pycache__/` 目录
- `.cursor/`, `.claude/` 等工具目录 (保留，不影响功能)

## 🔧 清理后的Makefile结构

```makefile
# 基础命令
install, clean, verify, check, help

# Pipeline V2 核心命令  
pipeline-v2
pipeline-v2-fast
pipeline-v2-nocache
pipeline-v2-products
pipeline-v2-export
pipeline-v2-test
pipeline-v2-test-clean

# 缓存管理
cache-status
cache-build
cache-classification
cache-products
cache-specifications
cache-rebuild
cache-clean-*

# 快捷命令
quick-start
full-refresh
```

## 📁 清理后的目录结构

```
50-爬虫01/
├── run_pipeline_v2.py          # 唯一入口
├── config.py
├── requirements.txt
├── README.md
├── Makefile                    # 精简版
├── src/
│   ├── auth/                   # 认证模块
│   ├── utils/                  # 工具模块
│   ├── pipelines/
│   │   ├── optimized_full_pipeline_v2.py
│   │   └── cache_manager.py
│   └── crawler/                # 核心爬虫 (精简)
├── results/                    # 结果目录
├── config/                     # 配置目录
└── docs/                       # 相关文档 (选择性)
```

## ⚡ 执行步骤

1. **备份确认** - 确保已经备份
2. **删除测试目录** - `rm -rf test/`
3. **清理脚本目录** - 选择性删除 `scripts/` 中的文件
4. **删除根目录文件** - 删除非核心的 `.py` 文件
5. **清理src目录** - 删除非V2的pipeline和过时crawler
6. **精简Makefile** - 只保留pipeline-v2相关命令
7. **清理结果目录** - `rm -rf results/*` 但保留目录结构
8. **测试功能** - 确保 `make pipeline-v2` 正常工作

## 🎯 预期效果

- **代码量减少 70-80%**
- **只保留一个入口**: `make pipeline-v2`
- **清晰的依赖关系**
- **专注的功能范围**
- **易于维护和部署**

## ⚠️ 注意事项

1. 删除前确保了解每个文件的作用
2. 部分crawler模块可能有交叉依赖，需要仔细检查
3. 保留必要的配置文件和工具函数
4. 确保pipeline-v2的完整功能链不被破坏 