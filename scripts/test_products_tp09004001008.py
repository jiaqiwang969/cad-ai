#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 products 功能脚本
=====================
使用最新的 ProductLinksCrawler 测试指定大页面，输出产品数量、耗时与部分链接示例。
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def run_test():
    url = (
        "https://www.traceparts.cn/en/search/traceparts-classification-"
        "electrical-electrical-protection-devices-circuit-breakers-"
        "molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    )
    expected = 5099  # 目标产品数

    print("🎯 TraceParts Products 功能验证")
    print("=" * 80)
    print(f"测试 URL : {url}")
    print(f"目标产品数 : {expected}\n")

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
        print(f"完成率     : {len(links)/expected*100:.2f}%\n")

        # 显示前 10 个链接示例
        sample_count = min(10, len(links))
        print("示例链接 (前 10)")
        for i in range(sample_count):
            print(f"{i+1:2d}. {links[i]}")

        # 评估
        if len(links) >= expected * 0.98:
            print("\n🎉 成功: 获取了几乎全部产品！")
        elif len(links) >= expected * 0.8:
            print("\n✅ 良好: 获取了大部分产品，可进一步优化。")
        else:
            print("\n⚠️  需要优化: 获取产品不足。")

    finally:
        bm.shutdown()
        print("\n✅ 测试完成")


if __name__ == "__main__":
    run_test() 