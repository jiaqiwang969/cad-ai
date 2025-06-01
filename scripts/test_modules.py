#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块测试脚本
===========
验证新架构各个组件是否正常工作
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from config.logging_config import get_logger

logger = get_logger(__name__)


def test_config():
    """测试配置管理"""
    print("\n📋 测试配置管理...")
    try:
        print(f"✅ 项目根目录: {Settings.PROJECT_ROOT}")
        print(f"✅ 最大并发数: {Settings.CRAWLER['max_workers']}")
        print(f"✅ 网络阈值: {Settings.NETWORK['fail_threshold']}")
        print(f"✅ 缓存目录: {Settings.STORAGE['cache_dir']}")
        return True
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False


def test_logging():
    """测试日志系统"""
    print("\n📝 测试日志系统...")
    try:
        logger.info("这是一条信息日志")
        logger.warning("这是一条警告日志")
        logger.error("这是一条错误日志")
        print("✅ 日志系统正常")
        return True
    except Exception as e:
        print(f"❌ 日志测试失败: {e}")
        return False


def test_net_guard():
    """测试网络监控"""
    print("\n🌐 测试网络监控...")
    try:
        from src.utils.net_guard import register_success, register_fail, get_network_stats
        
        # 测试记录成功
        register_success()
        register_success()
        
        # 测试记录失败
        register_fail('test')
        
        # 获取统计
        stats = get_network_stats()
        print(f"✅ 成功次数: {stats['total_successes']}")
        print(f"✅ 失败次数: {stats['total_failures']}")
        print(f"✅ 成功率: {stats['success_rate']:.1%}")
        return True
    except Exception as e:
        print(f"❌ 网络监控测试失败: {e}")
        return False


def test_browser_manager():
    """测试浏览器管理器"""
    print("\n🌏 测试浏览器管理器...")
    try:
        from src.utils.browser_manager import create_browser_manager
        
        # 创建管理器
        manager = create_browser_manager(pool_size=2)
        print(f"✅ 创建浏览器管理器: {manager.browser_type}")
        
        # 获取统计
        stats = manager.get_stats()
        print(f"✅ 浏览器池大小: {stats['pool_size']}")
        
        # 注意：不实际创建浏览器，避免需要Chrome
        print("✅ 浏览器管理器正常（跳过实际浏览器测试）")
        return True
    except Exception as e:
        print(f"❌ 浏览器管理器测试失败: {e}")
        return False


def test_crawlers():
    """测试爬虫模块导入"""
    print("\n🕷️ 测试爬虫模块...")
    try:
        from src.crawler.classification import ClassificationCrawler
        from src.crawler.products import ProductLinksCrawler
        from src.crawler.specifications import SpecificationsCrawler
        
        print("✅ ClassificationCrawler 导入成功")
        print("✅ ProductLinksCrawler 导入成功")
        print("✅ SpecificationsCrawler 导入成功")
        return True
    except Exception as e:
        print(f"❌ 爬虫模块测试失败: {e}")
        return False


def test_pipeline():
    """测试流水线模块"""
    print("\n🚀 测试流水线模块...")
    try:
        from src.pipelines.full_pipeline import FullPipeline
        
        # 创建流水线实例（不运行）
        pipeline = FullPipeline(max_workers=1)
        print("✅ FullPipeline 创建成功")
        
        # 测试统计
        print(f"✅ 初始统计: 叶节点={pipeline.stats['total_leaves']}")
        return True
    except Exception as e:
        print(f"❌ 流水线测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 开始测试新架构模块")
    print("=" * 60)
    
    tests = [
        test_config,
        test_logging,
        test_net_guard,
        test_browser_manager,
        test_crawlers,
        test_pipeline,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 测试完成: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    if failed == 0:
        print("✅ 所有测试通过！新架构工作正常。")
        print("\n下一步:")
        print("1. 运行 `make pipeline` 测试完整流程")
        print("2. 查看 `docs/architecture.md` 了解架构详情")
    else:
        print("❌ 有测试失败，请检查相关模块。")
        sys.exit(1)


if __name__ == '__main__':
    main() 