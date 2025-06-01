#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能对比测试
===========
对比不同日志级别和实现方式的性能差异
"""

import sys
import os
import time
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def test_with_different_log_levels():
    """测试不同日志级别的性能差异"""
    url = (
        "https://www.traceparts.cn/en/search/traceparts-classification-"
        "electrical-electrical-protection-devices-circuit-breakers-"
        "molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    )
    
    print("🎯 性能对比测试")
    print("=" * 80)
    
    # 测试不同日志级别
    for level_name, level in [('INFO', logging.INFO), ('DEBUG', logging.DEBUG)]:
        print(f"\n测试日志级别: {level_name}")
        print("-" * 40)
        
        # 设置日志级别
        logging.getLogger().setLevel(level)
        for handler in logging.getLogger().handlers:
            handler.setLevel(level)
        
        # 创建新的爬虫实例
        bm = create_browser_manager(pool_size=1)
        crawler = ProductLinksCrawler(bm)
        
        start_time = time.time()
        try:
            links = crawler.extract_product_links(url)
            elapsed = time.time() - start_time
            
            print(f"  获取产品数: {len(links)}")
            print(f"  用时: {elapsed:.1f} 秒")
            print(f"  平均速度: {len(links)/elapsed:.1f} 个/秒")
            
        except Exception as e:
            print(f"  错误: {e}")
            elapsed = time.time() - start_time
            print(f"  失败用时: {elapsed:.1f} 秒")
        finally:
            bm.shutdown()
    
    print("\n" + "=" * 80)
    print("🔍 性能分析建议:")
    print("1. DEBUG日志会产生大量输出，严重影响性能")
    print("2. 生产环境建议使用 INFO 或 WARNING 级别")
    print("3. 如需调试，可以针对特定模块开启DEBUG")


if __name__ == "__main__":
    test_with_different_log_levels() 