#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极性能爬取器测试
================
使用 UltimateProductLinksCrawler 测试终极性能
"""

import sys
import os
import time
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.ultimate_products import UltimateProductLinksCrawler

# 设置日志级别
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def run_ultimate_crawler_test():
    url = (
        "https://www.traceparts.cn/en/search/traceparts-classification-"
        "electrical-electrical-protection-devices-circuit-breakers-"
        "molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    )
    expected = 5099

    print("🚀 TraceParts 终极性能爬取器测试")
    print("=" * 80)
    print(f"测试 URL : {url}")
    print(f"目标产品数 : {expected}")
    print(f"爬取器类型 : UltimateProductLinksCrawler")
    print(f"特点       : 消除所有微小开销，达到极致性能")
    print()

    # 创建终极性能爬取器
    crawler = UltimateProductLinksCrawler(log_level=logging.INFO)

    start = time.time()
    links = crawler.extract_product_links(url, expected)
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

    # 性能说明
    print(f"\n🚀 终极性能优化特点:")
    print(f"   - 预编译所有配置常量 (避免Settings动态读取)")
    print(f"   - 简化按钮选择器 (4个 vs 13个)")
    print(f"   - 移除5秒等待循环")
    print(f"   - 预编译JavaScript代码")
    print(f"   - 去除所有网络监控调用")
    print(f"   - 一次性日志设置 (避免LoggerMixin)")
    print(f"   - 预编译抖动滚动位置")

    print("\n✅ 测试完成")


if __name__ == "__main__":
    run_ultimate_crawler_test() 