# Makefile for API testing
# Project: OpenAI API 爬虫测试项目

.PHONY: test test-openai test-langchain test-scraping test-async install clean help verify check list results benchmark

# Python executable
PYTHON := python3

# 确保项目根目录加入 PYTHONPATH，避免 utils 包与系统同名冲突
export PYTHONPATH := $(CURDIR)

# Test directory
TEST_DIR := test

# 默认 TraceParts 账号（可在运行 make 时覆盖）
TRACEPARTS_EMAIL ?= SearcherKerry36154@hotmail.com
TRACEPARTS_PASSWORD ?= Vsn220mh@

# Default target
all: help

# Install dependencies
install:
	@echo "🔧 安装依赖包..."
	$(PYTHON) -m pip install -r requirements.txt --break-system-packages
	@echo "📥 安装 Playwright 浏览器内核 (chromium)..."
	-$(PYTHON) -m playwright install chromium --with-deps 2>/dev/null || true

# Run all tests
test: test-openai test-langchain test-scraping test-async
	@echo ""
	@echo "🎉 所有测试完成！"

# Run OpenAI API test
test-openai:
	@echo "=" * 60
	@echo "🧪 运行 OpenAI API 测试..."
	@echo "=" * 60
	$(PYTHON) $(TEST_DIR)/01-test_openai_api.py
	@echo ""

# Run LangChain test
test-langchain:
	@echo "=" * 60
	@echo "🧪 运行 LangChain API 测试..."
	@echo "=" * 60
	$(PYTHON) $(TEST_DIR)/02-test_langchain_api.py
	@echo ""

# Run Web Scraping test
test-scraping:
	@echo "=" * 60
	@echo "🧪 运行 LangChain 网页爬取测试..."
	@echo "=" * 60
	$(PYTHON) $(TEST_DIR)/03-test_langchain_web_scraping.py
	@echo ""

# Run Async Web Scraping test
test-async:
	@echo "=" * 60
	@echo "🧪 运行异步并发网页爬取测试..."
	@echo "=" * 60
	$(PYTHON) $(TEST_DIR)/04-test_async_web_scraping.py
	@echo ""

# Run specific test by number
test-01:
	@echo "🧪 运行测试 01: OpenAI API..."
	$(PYTHON) $(TEST_DIR)/01-test_openai_api.py

test-02:
	@echo "🧪 运行测试 02: LangChain API..."
	$(PYTHON) $(TEST_DIR)/02-test_langchain_api.py

test-03:
	@echo "🧪 运行测试 03: LangChain 网页爬取..."
	$(PYTHON) $(TEST_DIR)/03-test_langchain_web_scraping.py

test-04:
	@echo "🧪 运行测试 04: 异步并发网页爬取..."
	$(PYTHON) $(TEST_DIR)/04-test_async_web_scraping.py

# Run test 05: Category Drill Down
test-05:
	@echo "🧪 运行测试 05: 类目深度爬取..."
	$(PYTHON) $(TEST_DIR)/05-test_category_drill_down.py

# Run test 06: complete classification tree
test-06:
	@echo "🔎 运行测试 06: TraceParts 完整分类树提取..."
	$(PYTHON) $(TEST_DIR)/06-test_classification_tree_recursive.py

# Run test 07: build nested tree
test-07:
	@echo "🌳 运行测试 07: 构建嵌套分类树..."
	$(PYTHON) $(TEST_DIR)/07-test_classification_tree_nested.py

# Run test 08: collect product links for a leaf category
test-08:
	@echo "📦 运行测试 08: 叶节点产品链接提取..."
	$(PYTHON) $(TEST_DIR)/08-test_leaf_product_links.py

# Run test 09: batch leaf product links
test-09:
	@echo "🚀 运行测试 09: 批量叶节点产品链接提取..."
	$(PYTHON) $(TEST_DIR)/09-test_batch_leaf_product_links.py

# Run test 09-1: Product specifications link extractor
test-09-1:
	@echo "🔗 运行测试 09-1: 产品规格链接提取器..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) $(TEST_DIR)/09-1-test_product_specifications_extractor.py

# Run test 09-1-v2: Product specifications link extractor (集成版本)
test-09-1-v2:
	@echo "🔗 运行测试 09-1-v2: 产品规格链接提取器 (集成版本)..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) $(TEST_DIR)/09-1-test_product_specifications_extractor_v2.py

# Run test 09-2: Universal product specifications extractor
test-09-2:
	@echo "🌐 运行测试 09-2: 通用产品规格提取器..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) $(TEST_DIR)/09-2-test_universal_specifications_extractor.py

# Run test 10: Ultimate automatic CAD download
test-10:
	@echo "🎯 运行测试 10: 终极自动 CAD 下载..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) $(TEST_DIR)/10-test_product_cad_download.py

# Run test 11: Independent full pipeline (traceparts_full_pipeline.py)
test-11:
	@echo "🌐 运行测试 11: TraceParts 全链条抓取 (独立版)..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) traceparts_full_pipeline.py --workers 32

# Run new modular pipeline
pipeline:
	@echo "🚀 运行新架构流水线..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_pipeline.py --workers 16

# Run pipeline with custom settings
pipeline-fast:
	@echo "⚡ 运行快速流水线 (32 workers)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_pipeline.py --workers 32

pipeline-nocache:
	@echo "🔄 运行流水线 (禁用缓存)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_pipeline.py --no-cache

# Run optimized pipeline
pipeline-optimized:
	@echo "🚀 运行优化版流水线 (终极性能)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_optimized_pipeline.py --workers 16

pipeline-optimized-max:
	@echo "⚡ 运行优化版流水线 (最大并发: 64)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_optimized_pipeline.py --workers 32

pipeline-optimized-nocache:
	@echo "🔄 运行优化版流水线 (禁用缓存)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_optimized_pipeline.py --no-cache

pipeline-optimized-test:
	@echo "🧪 运行优化版流水线测试 (迷你样本)..."
	@echo "   创建测试缓存..."
	@PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/create_test_cache.py
	@echo ""
	@echo "   运行优化版流水线..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_optimized_pipeline.py --workers 4

# ==================== 新版渐进式缓存系统 ====================
# Pipeline V2 - 基于渐进式缓存管理器
pipeline-v2:
	@echo "🚀 运行流水线 V2 (渐进式缓存系统)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_pipeline_v2.py --workers 16

pipeline-v2-fast:
	@echo "⚡ 运行流水线 V2 (最大并发: 64)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_pipeline_v2.py --workers 64

pipeline-v2-nocache:
	@echo "🔄 运行流水线 V2 (强制刷新)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_pipeline_v2.py --no-cache

pipeline-v2-products:
	@echo "📦 运行流水线 V2 (只到产品级别)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_pipeline_v2.py --level products

pipeline-v2-export:
	@echo "📄 运行流水线 V2 (导出到文件)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_pipeline_v2.py --output results/export_$(shell date +%Y%m%d_%H%M%S).json

pipeline-v2-products-test:
	@echo "🧪 运行流水线 V2 产品级别测试 (迷你样本)..."
	@echo "   创建迷你测试缓存..."
	@PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/create_mini_test_cache.py
	@echo ""
	@echo "   运行产品链接提取..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_pipeline_v2.py --level products --workers 4

pipeline-v2-test:
	@echo "🧪 运行流水线 V2 完整测试 (单叶节点)..."
	@echo "   创建单叶节点测试缓存..."
	@PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/create_single_test_cache.py
	@echo ""
	@echo "   运行完整流水线 (1个叶节点, 1个worker)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_pipeline_v2.py --workers 1

# Cache Manager - 缓存管理器
cache-build:
	@echo "🏗️ 构建完整缓存 (分类树+产品+规格)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_cache_manager.py --level specifications

cache-classification:
	@echo "🌳 构建分类树缓存..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_cache_manager.py --level classification

cache-products:
	@echo "📦 扩展产品链接缓存..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_cache_manager.py --level products

cache-specifications:
	@echo "📋 扩展产品规格缓存..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_cache_manager.py --level specifications

cache-rebuild:
	@echo "🔄 强制重建所有缓存..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) run_cache_manager.py --force

cache-status:
	@echo "📊 查看缓存状态..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/demo_progressive_cache.py

cache-extend:
	@echo "🔧 扩展现有缓存 (旧版兼容)..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) extend_cache.py

# 缓存清理命令扩展
cache-clean-products:
	@echo "🧹 清理产品链接缓存..."
	rm -rf results/cache/products/*
	@echo "✅ 产品缓存已清理"

cache-clean-specs:
	@echo "🧹 清理产品规格缓存..."
	rm -rf results/cache/specifications/*
	@echo "✅ 规格缓存已清理"

cache-backup:
	@echo "💾 备份缓存文件..."
	@mkdir -p results/cache_backup
	@cp results/cache/classification_tree_full.json results/cache_backup/classification_tree_full_$(shell date +%Y%m%d_%H%M%S).json 2>/dev/null || echo "❌ 无缓存文件可备份"
	@echo "✅ 缓存已备份"

cache-restore:
	@echo "📥 恢复缓存备份..."
	@cp results/cache/classification_tree_full.json.bak results/cache/classification_tree_full.json 2>/dev/null && echo "✅ 缓存已恢复" || echo "❌ 无备份文件"

# 快捷命令
quick-start:
	@echo "🚀 快速开始 (使用缓存)..."
	@make cache-status
	@make pipeline-v2

full-refresh:
	@echo "🔄 完全刷新 (清理并重建)..."
	@make clean-cache
	@make cache-rebuild

# Quick verification test
verify:
	@echo "🔄 快速验证 API 连接..."
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		if [ -f .env ]; then \
			export $$(cat .env | grep -v '^#' | xargs) && \
			curl -s -X POST $$OPENAI_BASE_URL/chat/completions \
				-H "Content-Type: application/json" \
				-H "Authorization: Bearer $$OPENAI_API_KEY" \
				-d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}' \
				| grep -q "choices" && echo "✅ API 连接正常" || echo "❌ API 连接失败"; \
		else \
			echo "❌ 未找到 .env 文件或 OPENAI_API_KEY 环境变量"; \
		fi \
	else \
		curl -s -X POST $$OPENAI_BASE_URL/chat/completions \
			-H "Content-Type: application/json" \
			-H "Authorization: Bearer $$OPENAI_API_KEY" \
			-d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}' \
			| grep -q "choices" && echo "✅ API 连接正常" || echo "❌ API 连接失败"; \
	fi

# Clean up
clean:
	@echo "🧹 清理临时文件..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf results/*.json 2>/dev/null || true
	rm -rf results/*.jsonl 2>/dev/null || true
	@echo "✅ 清理完成"

# List test files
list:
	@echo "📁 测试文件列表:"
	@ls -la $(TEST_DIR)/

# Check requirements
check:
	@echo "📋 检查依赖包..."
	@$(PYTHON) -c "import openai; print('✅ openai:', openai.__version__)" 2>/dev/null || echo "❌ openai 未安装"
	@$(PYTHON) -c "import langchain; print('✅ langchain:', langchain.__version__)" 2>/dev/null || echo "❌ langchain 未安装"
	@$(PYTHON) -c "import langchain_openai; print('✅ langchain_openai 已安装')" 2>/dev/null || echo "❌ langchain_openai 未安装"
	@$(PYTHON) -c "import bs4; print('✅ beautifulsoup4 已安装')" 2>/dev/null || echo "❌ beautifulsoup4 未安装"
	@$(PYTHON) -c "import requests; print('✅ requests 已安装')" 2>/dev/null || echo "❌ requests 未安装"
	@$(PYTHON) -c "import selenium; print('✅ selenium 已安装')" 2>/dev/null || echo "❌ selenium 未安装"
	@$(PYTHON) -c "import aiofiles; print('✅ aiofiles 已安装')" 2>/dev/null || echo "❌ aiofiles 未安装"

# Show results
results:
	@echo "📊 查看爬取结果..."
	@ls -la results/ 2>/dev/null || echo "❌ 暂无结果文件"

# Performance comparison
benchmark:
	@echo "🏃‍♂️ 运行性能对比测试..."
	@echo "运行同步版本..."
	@time $(PYTHON) $(TEST_DIR)/03-test_langchain_web_scraping.py
	@echo ""
	@echo "运行异步版本..."
	@time $(PYTHON) $(TEST_DIR)/04-test_async_web_scraping.py

# Help
help:
	@echo "🚀 OpenAI API 爬虫测试项目"
	@echo ""
	@echo "可用命令:"
	@echo "  make install        - 安装依赖包"
	@echo "  make test           - 运行所有测试"
	@echo "  make test-openai    - 只运行 OpenAI API 测试"
	@echo "  make test-langchain - 只运行 LangChain 测试"
	@echo "  make test-scraping  - 只运行网页爬取测试"
	@echo "  make test-async     - 只运行异步并发网页爬取测试"
	@echo "  make test-01        - 运行测试 01 (OpenAI API)"
	@echo "  make test-02        - 运行测试 02 (LangChain)"
	@echo "  make test-03        - 运行测试 03 (网页爬取)"
	@echo "  make test-04        - 运行测试 04 (异步并发爬取)"
	@echo "  make test-05        - 运行测试 05 (类目深度爬取)"
	@echo "  make test-06        - 运行测试 06 (完整分类树提取)"
	@echo "  make test-07        - 运行测试 07 (构建嵌套分类树)"
	@echo "  make test-08        - 运行测试 08 (叶节点产品链接提取)"
	@echo "  make test-09        - 运行测试 09 (批量叶节点产品链接提取)"
	@echo "  make test-09-1      - 运行测试 09-1 (🔗 产品规格链接提取器)"
	@echo "  make test-09-2      - 运行测试 09-2 (🌐 通用产品规格提取器)"
	@echo "  make test-10        - 运行测试 10 (🎯 终极自动 CAD 下载)"
	@echo "  make test-11        - 运行测试 11 (全流程一键抓取)"
	@echo "  make pipeline       - 🚀 运行新架构流水线 (推荐)"
	@echo "  make pipeline-fast  - ⚡ 运行快速流水线 (32 workers)"
	@echo "  make pipeline-nocache - 🔄 运行流水线 (禁用缓存)"
	@echo "  make pipeline-optimized - 🚀 运行优化版流水线 (终极性能)"
	@echo "  make pipeline-optimized-max - ⚡ 运行优化版流水线 (64 workers)"
	@echo "  make pipeline-optimized-nocache - 🔄 运行优化版流水线 (禁用缓存)"
	@echo "  make pipeline-optimized-test - 🧪 运行测试流水线 (5个叶节点)"
	@echo ""
	@echo "🆕 渐进式缓存系统 (V2):"
	@echo "  make pipeline-v2    - 🚀 运行流水线 V2 (推荐)"
	@echo "  make pipeline-v2-fast - ⚡ 运行流水线 V2 (64 workers)"
	@echo "  make pipeline-v2-nocache - 🔄 强制刷新所有数据"
	@echo "  make pipeline-v2-products - 📦 只爬取到产品级别"
	@echo "  make pipeline-v2-export - 📄 运行并导出结果"
	@echo "  make pipeline-v2-products-test - 🧪 产品级别测试 (2个叶节点)"
	@echo "  make pipeline-v2-test - 🧪 完整流程测试 (1个叶节点)"
	@echo ""
	@echo "📦 缓存管理:"
	@echo "  make cache-status   - 📊 查看缓存状态"
	@echo "  make cache-build    - 🏗️ 构建完整缓存"
	@echo "  make cache-classification - 🌳 只构建分类树"
	@echo "  make cache-products - 📦 扩展产品链接"
	@echo "  make cache-specifications - 📋 扩展产品规格"
	@echo "  make cache-rebuild  - 🔄 强制重建所有缓存"
	@echo "  make cache-backup   - 💾 备份缓存文件"
	@echo "  make cache-restore  - 📥 恢复缓存备份"
	@echo "  make cache-clean-products - 🧹 清理产品缓存"
	@echo "  make cache-clean-specs - 🧹 清理规格缓存"
	@echo ""
	@echo "⚡ 快捷命令:"
	@echo "  make quick-start    - 🚀 快速开始 (查看状态并运行)"
	@echo "  make full-refresh   - 🔄 完全刷新 (清理并重建)"
	@echo ""
	@echo "  make verify         - 快速验证 API 连接"
	@echo "  make check          - 检查依赖包状态"
	@echo "  make list           - 列出测试文件"
	@echo "  make results        - 查看爬取结果文件"
	@echo "  make benchmark      - 性能对比测试"
	@echo "  make clean          - 清理临时文件"
	@echo "  make clean-cache    - 清理缓存文件"
	@echo "  make clean-all      - 清理所有结果文件"
	@echo ""
	@echo "🔍 监控与运维:"
	@echo "  make monitor        - 启动健康监控（持续运行）"
	@echo "  make monitor-once   - 运行单次健康检查"
	@echo "  make health-check   - 健康检查（同 monitor-once）"
	@echo "  make status         - 查看系统状态"
	@echo "  make logs           - 查看最近日志"
	@echo "  make logs-monitor   - 查看监控日志"
	@echo "  make logs-follow    - 实时跟踪日志"
	@echo ""
	@echo "🚀 部署管理:"
	@echo "  make deploy         - 部署到生产环境"
	@echo "  make deploy-rollback - 回滚部署"
	@echo ""
	@echo "  make help           - 显示此帮助信息"
	@echo ""
	@echo "示例："
	@echo "  make install && make test"
	@echo "  make test-04         # 只运行异步并发爬取测试"
	@echo "  make benchmark       # 对比同步vs异步性能"
	@echo "  make pipeline-optimized && make monitor  # 运行优化版并监控"

# 清理命令
clean-cache:
	@echo "🧹 清理缓存..."
	rm -rf results/cache/*
	@echo "✅ 缓存已清理"

clean-all: clean clean-cache
	@echo "🧹 清理所有结果..."
	rm -rf results/products/*
	rm -rf results/export/*
	@echo "✅ 所有结果已清理"

# 监控命令
monitor:
	@echo "🔍 启动健康监控..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/health_monitor.py

monitor-once:
	@echo "🔍 运行单次健康检查..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/health_monitor.py --once

health-check: monitor-once

# 部署命令
deploy:
	@echo "🚀 部署到生产环境..."
	chmod +x scripts/deploy_production.sh
	./scripts/deploy_production.sh deploy

deploy-rollback:
	@echo "⏪ 回滚部署..."
	./scripts/deploy_production.sh rollback

# 生产环境快速启动
production-start:
	@echo "🚀 启动生产环境..."
	chmod +x scripts/start_production.sh
	./scripts/start_production.sh start

production-stop:
	@echo "🛑 停止生产环境..."
	./scripts/start_production.sh stop

production-restart:
	@echo "🔄 重启生产环境..."
	./scripts/start_production.sh restart

production-status:
	@echo "📊 生产环境状态..."
	./scripts/start_production.sh status

# 日志查看
logs:
	@echo "📋 查看最近日志..."
	@tail -n 100 logs/opt-pipeline.log 2>/dev/null || echo "暂无日志文件"

logs-monitor:
	@echo "📋 查看监控日志..."
	@tail -n 100 logs/health_monitor.log 2>/dev/null || echo "暂无监控日志"

logs-follow:
	@echo "📋 实时查看日志..."
	@tail -f logs/opt-pipeline.log 2>/dev/null || echo "暂无日志文件"

# 测试修复
test-fix:
	@echo "🔧 测试产品链接提取修复..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/test_product_fix.py

# 系统状态
status:
	@echo "📊 系统状态..."
	@echo "进程状态:"
	@ps aux | grep -E "(optimized_full_pipeline|health_monitor)" | grep -v grep || echo "  没有运行中的进程"
	@echo "\n磁盘使用:"
	@df -h | grep -E "(/$|results)" || true
	@echo "\n内存使用:"
	@free -h 2>/dev/null || vm_stat 2>/dev/null || echo "  无法获取内存信息"
	@echo "\n最近的结果文件:"
	@ls -lht results/products/*.json 2>/dev/null | head -5 || echo "  暂无结果文件"

# 调试工具
debug-zero-specs:
	@echo "🔍 收集规格数为0的产品链接..."
	@python3 scripts/debug_zero_specs_collector.py --sample-size 20

debug-zero-specs-full:
	@echo "🔍 收集规格数为0的产品链接（大样本）..."
	@python3 scripts/debug_zero_specs_collector.py --sample-size 100

debug-specific-urls:
	@echo "🧪 测试特定URL..."
	@python3 scripts/debug_zero_specs_collector.py --test-specific 