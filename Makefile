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

# Run test 10: product CAD download demo
test-10:
	@echo "📐 运行测试 10: 单产品 CAD 下载示例..."
	$(PYTHON) $(TEST_DIR)/10-test_product_cad_download.py

# Run test 11: login and session save
test-11:
	@echo "🔑 运行测试 11: 登录并保存 Cookies..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) \
	$(PYTHON) $(TEST_DIR)/11-test_login_and_session.py

# Run test 12: capture captcha image
test-12:
	@echo "🖼️ 运行测试 12: 触发验证码并保存图片..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) $(TEST_DIR)/12-test_capture_captcha.py

# Run test 11d: login and navigate to product pages
test-11d:
	@echo "🛒 运行测试 11d: 登录并跳转产品页面..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) \
	$(PYTHON) $(TEST_DIR)/11d-test_login_and_navigate.py

# Run test 11e: stealth CAD download
test-11e:
	@echo "🥷 运行测试 11e: 强化反检测CAD下载..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) \
	$(PYTHON) $(TEST_DIR)/11e-test_stealth_cad_download.py

# Run test 11f: real Chrome browser
test-11f:
	@echo "🌐 运行测试 11f: 真实Chrome浏览器测试..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) \
	$(PYTHON) $(TEST_DIR)/11f-test_real_chrome.py

# Run test 11g: TraceParts detection mechanism diagnosis
test-11g:
	@echo "🔬 运行测试 11g: TraceParts检测机制诊断..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) \
	$(PYTHON) $(TEST_DIR)/11g-diagnose_traceparts_detection.py

# Run test 11h: advanced CAD access analysis
test-11h:
	@echo "🔬 运行测试 11h: 高级CAD访问分析..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) \
	$(PYTHON) $(TEST_DIR)/11h-advanced_cad_access.py

# Run test 11i: stealth CAD downloader
test-11i:
	@echo "🥷 运行测试 11i: 隐身CAD下载器..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) \
	$(PYTHON) $(TEST_DIR)/11i-stealth_cad_downloader.py

# Run test 13: OCR captcha
test-13:
	@echo "🔍 运行测试 13: 验证码 OCR 识别..."
	$(PYTHON) $(TEST_DIR)/13-test_ocr_captcha.py

# Run test 12h: auto captcha solve & download
test-12h:
	@echo "🔑 运行测试 12h: 自动识别验证码并下载 CAD..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) $(TEST_DIR)/12h-auto_captcha_download.py

# Quick verification test
verify:
	@echo "🔍 快速验证 API 连接..."
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

# Run test 11j: stealth download with captcha
test-11j:
	@echo "🔑 运行测试 11j: 隐身 CAD 下载 + 自动验证码..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) \
	$(PYTHON) $(TEST_DIR)/11j-stealth_cad_downloader_captcha.py

# Run test 12k: extract captcha region and OCR
test-12k:
	@echo "🎯 运行测试 12k: 精确提取验证码区域并OCR识别..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) $(TEST_DIR)/12k-extract_captcha_region.py

# Run test K: GPT-4o auto captcha download
test-k:
	@echo "🤖 运行测试 K: GPT-4o 自动验证码下载..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) $(TEST_DIR)/k-auto_captcha_download.py

# Run test L: minimal captcha extraction
test-l:
	@echo "🔎 运行测试 L: 极简验证码提取..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) PYTHONPATH=$(PYTHONPATH) \
	$(PYTHON) $(TEST_DIR)/l-extract_captcha.py

# Run test j: auto captcha download
test-j:
	@echo "🔑 运行测试 j: 自动验证码下载..."
	TRACEPARTS_EMAIL=$(TRACEPARTS_EMAIL) TRACEPARTS_PASSWORD=$(TRACEPARTS_PASSWORD) PYTHONPATH=$(PWD) \
	$(PYTHON) $(TEST_DIR)/j-auto_captcha_download.py

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
	@echo "  make test-10        - 运行测试 10 (单产品 CAD 下载示例)"
	@echo "  make test-11        - 运行测试 11 (登录并保存 Cookies)"
	@echo "  make test-11g       - 运行测试 11g (TraceParts检测机制诊断)"
	@echo "  make test-12        - 运行测试 12 (捕获验证码图片)"
	@echo "  make test-13        - 运行测试 13 (OCR 验证码识别)"
	@echo "  make test-12h       - 运行测试 12h (自动识别验证码并下载 CAD)"
	@echo "  make test-12k       - 运行测试 12k (精确提取验证码区域并OCR识别)"
	@echo "  make test-k         - 运行测试 K (GPT-4o 自动验证码下载)"
	@echo "  make test-l         - 运行测试 L (极简验证码提取)"
	@echo "  make test-j         - 运行测试 j (自动验证码下载)"
	@echo "  make verify         - 快速验证 API 连接"
	@echo "  make check          - 检查依赖包状态"
	@echo "  make list           - 列出测试文件"
	@echo "  make results        - 查看爬取结果文件"
	@echo "  make benchmark      - 性能对比测试"
	@echo "  make clean          - 清理临时文件"
	@echo "  make help           - 显示此帮助信息"
	@echo ""
	@echo "示例："
	@echo "  make install && make test"
	@echo "  make test-04         # 只运行异步并发爬取测试"
	@echo "  make benchmark       # 对比同步vs异步性能" 