#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境配置
============
优化版Pipeline生产环境配置参数
"""

import os
from pathlib import Path

# 基础配置
ENV = "production"
DEBUG = False
LOG_LEVEL = "INFO"

# 并发配置
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "32"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

# 路径配置
BASE_DIR = Path(__file__).parent.parent
RESULTS_DIR = BASE_DIR / "results"
CACHE_DIR = RESULTS_DIR / "cache"
PRODUCTS_DIR = RESULTS_DIR / "products"
LOGS_DIR = BASE_DIR / "logs"

# 缓存配置
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))  # 24小时
CLASSIFICATION_CACHE_TTL = int(os.getenv("CLASSIFICATION_CACHE_TTL", "604800"))  # 7天

# 重试配置
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))

# 监控配置
MONITOR_ENABLED = os.getenv("MONITOR_ENABLED", "true").lower() == "true"
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "300"))  # 5分钟
ALERT_WEBHOOK = os.getenv("ALERT_WEBHOOK", "")

# 性能配置
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
DISABLE_IMAGES = os.getenv("DISABLE_IMAGES", "true").lower() == "true"
DISABLE_CSS = os.getenv("DISABLE_CSS", "false").lower() == "true"

# 数据库配置（如果需要）
DB_ENABLED = os.getenv("DB_ENABLED", "false").lower() == "true"
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "traceparts")
DB_USER = os.getenv("DB_USER", "traceparts")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# 输出配置
OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "json")  # json, csv, both
COMPRESS_OUTPUT = os.getenv("COMPRESS_OUTPUT", "true").lower() == "true"

# 任务调度配置
SCHEDULE_ENABLED = os.getenv("SCHEDULE_ENABLED", "false").lower() == "true"
SCHEDULE_CRON = os.getenv("SCHEDULE_CRON", "0 2 * * *")  # 每天凌晨2点

# 确保必要目录存在
for directory in [RESULTS_DIR, CACHE_DIR, PRODUCTS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# 导出配置字典
CONFIG = {
    "env": ENV,
    "debug": DEBUG,
    "log_level": LOG_LEVEL,
    "max_workers": MAX_WORKERS,
    "batch_size": BATCH_SIZE,
    "request_timeout": REQUEST_TIMEOUT,
    "paths": {
        "base": str(BASE_DIR),
        "results": str(RESULTS_DIR),
        "cache": str(CACHE_DIR),
        "products": str(PRODUCTS_DIR),
        "logs": str(LOGS_DIR)
    },
    "cache": {
        "enabled": CACHE_ENABLED,
        "ttl": CACHE_TTL,
        "classification_ttl": CLASSIFICATION_CACHE_TTL
    },
    "retry": {
        "max_retries": MAX_RETRIES,
        "delay": RETRY_DELAY
    },
    "monitor": {
        "enabled": MONITOR_ENABLED,
        "health_check_interval": HEALTH_CHECK_INTERVAL,
        "alert_webhook": ALERT_WEBHOOK
    },
    "performance": {
        "headless": HEADLESS,
        "disable_images": DISABLE_IMAGES,
        "disable_css": DISABLE_CSS
    },
    "output": {
        "format": OUTPUT_FORMAT,
        "compress": COMPRESS_OUTPUT
    }
} 