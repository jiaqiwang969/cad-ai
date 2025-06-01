#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版产品功能测试
================
使用 INFO 日志级别测试 ProductLinksCrawler 性能
"""

import sys
import os
import time
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager

# 设置优化的日志级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def run_optimized_test():
    url = (
        "https://www.traceparts.cn/en/search/traceparts-classification-"
        "electrical-electrical-protection-devices-circuit-breakers-"
        "molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    )
    expected = 5099

    print("🎯 TraceParts Products 性能优化测试")
    print("=" * 80)
    print(f"测试 URL : {url}")
    print(f"目标产品数 : {expected}")
    print(f"日志级别 : INFO (优化性能)")
    print()

    bm = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(bm)

    try:
        start = time.time()
        links = crawler.extract_product_links(url)
        elapsed = time.time() - start

        print("\n测试结果")
        print("-" * 80)
        print(f"获取产品数 : {len(links)}")
        print(f"用时       : {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
        if elapsed > 0:
            print(f"平均速度   : {len(links)/elapsed:.1f} 个/秒")
        print(f"完成率     : {len(links)/expected*100:.2f}%")

        # 显示前 5 个链接示例
        sample_count = min(5, len(links))
        print(f"\n示例链接 (前 {sample_count} 个)")
        for i in range(sample_count):
            print(f"{i+1:2d}. {links[i]}")

        # 性能评估
        if len(links) >= expected * 0.98:
            print("\n🎉 优秀: 获取了几乎全部产品！")
        elif len(links) >= expected * 0.9:
            print("\n✅ 良好: 获取了大部分产品。")
        elif len(links) >= expected * 0.7:
            print("\n⚠️  一般: 获取产品较多，可进一步优化。")
        else:
            print("\n❌ 需要优化: 获取产品不足。")

        # 性能对比提示
        print(f"\n💡 性能提示:")
        print(f"   - 当前使用 INFO 日志级别，性能优化")
        print(f"   - 如需详细调试信息，可使用 LOG_LEVEL=DEBUG")
        print(f"   - DEBUG 模式会显著降低性能，仅建议调试时使用")

    finally:
        bm.shutdown()
        print("\n✅ 测试完成")


if __name__ == "__main__":
    run_optimized_test() 