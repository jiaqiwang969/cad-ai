#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局配置管理
===========
统一管理项目的所有配置项
"""

import os
from pathlib import Path
from typing import List, Dict, Any

class Settings:
    """全局配置类"""
    
    # ========== 路径配置 ==========
    PROJECT_ROOT = Path(__file__).parent.parent
    RESULTS_DIR = PROJECT_ROOT / 'results'
    CACHE_DIR = RESULTS_DIR / 'cache'
    DOWNLOAD_DIR = RESULTS_DIR / 'downloads'
    
    # ========== 爬虫配置 ==========
    CRAWLER = {
        'max_workers': int(os.getenv('MAX_WORKERS', '16')),
        'min_workers': 4,
        'browser_pool_size': int(os.getenv('BROWSER_POOL_SIZE', '16')),  # 与max_workers保持一致
        'timeout': 60,
        'page_load_timeout': 90,
        'retry_times': 3,
        'retry_delay': 5,
        'scroll_pause': 1.3,
        'headless': True,  # 是否使用无头模式
        'user_agents': [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ],
    }
    
    # ========== 存储配置 ==========
    # 使用方法来动态生成路径，避免类定义时的问题
    @classmethod
    def _get_storage(cls):
        return {
            'database': f'sqlite:///{cls.RESULTS_DIR}/crawler.db',
            'cache_dir': str(cls.CACHE_DIR),
            'download_dir': str(cls.DOWNLOAD_DIR),
            'products_dir': str(cls.RESULTS_DIR / 'products'),
            'logs_dir': str(cls.RESULTS_DIR / 'logs'),
            'cache_ttl': 86400,  # 24小时
        }
    
    # 初始化存储配置
    STORAGE = {
        'database': '',  # 将在 ensure_dirs 中设置
        'cache_dir': '',
        'download_dir': '',
        'products_dir': '',
        'logs_dir': '',
        'cache_ttl': 86400,  # 24小时
    }
    
    # ========== 认证配置 ==========
    AUTH = {
        'accounts': [
            {
                'email': os.getenv('TRACEPARTS_EMAIL', 'SearcherKerry36154@hotmail.com'),
                'password': os.getenv('TRACEPARTS_PASSWORD', 'Vsn220mh@')
            }
        ],
        'session_timeout': 3600,
        'session_file': str(RESULTS_DIR / 'session_cookies.json'),
    }
    
    # ========== 网络配置 ==========
    NETWORK = {
        'fail_window_sec': 180,     # 3分钟统计窗口
        'fail_threshold': 5,        # 失败阈值
        'pause_seconds': 120,       # 暂停时间
        'cooldown_factor': 0.5,     # 冷却期系数
    }
    
    # ========== URL配置 ==========
    URLS = {
        'root': 'https://www.traceparts.cn/en/search/traceparts-classification?CatalogPath=TRACEPARTS%3ATRACEPARTS',
        'login': 'https://www.traceparts.cn/en/sign-in',
        'base': 'https://www.traceparts.cn',
    }
    
    # ========== 重试策略 ==========
    RETRY_STRATEGIES = {
        'network_error': {
            'max_retry': 5,
            'delay': lambda attempt: attempt * 2,  # 指数退避
        },
        'captcha_error': {
            'max_retry': 3,
            'delay': lambda attempt: 1,
        },
        'auth_error': {
            'max_retry': 2,
            'delay': lambda attempt: 60,
        },
        'parse_error': {
            'max_retry': 1,
            'delay': lambda attempt: 0,
        },
        'timeout_error': {
            'max_retry': 3,
            'delay': lambda attempt: attempt * 5,
        }
    }
    
    # ========== 验证码配置 ==========
    CAPTCHA = {
        'solver': os.getenv('CAPTCHA_SOLVER', 'gpt4o'),  # gpt4o, trocr, manual
        'gpt4o_api_key': os.getenv('GPT4O_API_KEY', os.getenv('OPENAI_API_KEY')),
        'gpt4o_base_url': os.getenv('GPT4O_BASE_URL', 'https://ai.pumpkinai.online/v1'),
        'debug': os.getenv('CAPTCHA_DEBUG', 'false').lower() == 'true',
        'debug_dir': str(RESULTS_DIR / 'captcha_debug'),
    }
    
    # ========== 日志配置 ==========
    LOGGING = {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'format': '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        'file': str(RESULTS_DIR / 'logs' / 'crawler.log'),
        'max_bytes': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5,
    }
    
    # ========== 并发控制 ==========
    CONCURRENCY = {
        'dynamic_adjustment': True,
        'success_rate_threshold_up': 0.9,    # 成功率高于此值时增加并发
        'success_rate_threshold_down': 0.7,  # 成功率低于此值时减少并发
        'adjustment_interval': 60,           # 调整间隔（秒）
        'worker_increment': 2,               # 每次调整的worker数
    }
    
    @classmethod
    def ensure_dirs(cls):
        """确保所有必要的目录存在"""
        # 更新存储配置
        cls.STORAGE.update(cls._get_storage())
        
        dirs = [
            cls.RESULTS_DIR,
            cls.CACHE_DIR,
            cls.DOWNLOAD_DIR,
            cls.RESULTS_DIR / 'products',
            cls.RESULTS_DIR / 'logs',
            cls.RESULTS_DIR / 'captcha_debug',
            cls.RESULTS_DIR / 'products_meta',
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_user_agent(cls, index: int = 0) -> str:
        """获取用户代理字符串"""
        agents = cls.CRAWLER['user_agents']
        return agents[index % len(agents)]
    
    @classmethod
    def get_retry_strategy(cls, error_type: str) -> Dict[str, Any]:
        """获取重试策略"""
        return cls.RETRY_STRATEGIES.get(
            error_type,
            cls.RETRY_STRATEGIES['network_error']
        )


# 初始化时确保目录存在
Settings.ensure_dirs() 