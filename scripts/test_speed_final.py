#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终速度测试
============
验证优化后的爬虫速度
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def test_speed_final():
    """测试优化后的速度"""
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("🚀 最终速度测试 - 优化版本")
    print("=" * 80)
    print(f"URL: {url}")
    print("期望: 145个产品，用时<10秒")
    print("=" * 80)
    
    # 多次测试取平均值
    times = []
    results = []
    
    browser_manager = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(browser_manager)
    
    try:
        for i in range(3):
            print(f"\n🔄 第 {i+1} 次测试...")
            start_time = time.time()
            
            # 提取产品
            products = crawler.extract_product_links(url)
            
            elapsed = time.time() - start_time
            times.append(elapsed)
            results.append(len(products))
            
            print(f"  ✓ 完成：{len(products)} 个产品，用时 {elapsed:.1f} 秒")
            
            # 短暂休息避免被限制
            if i < 2:
                time.sleep(2)
        
        # 统计结果
        avg_time = sum(times) / len(times)
        avg_products = sum(results) / len(results)
        
        print("\n📊 测试结果汇总：")
        print(f"  - 平均用时: {avg_time:.1f} 秒")
        print(f"  - 平均产品数: {avg_products:.0f}")
        print(f"  - 最快用时: {min(times):.1f} 秒")
        print(f"  - 最慢用时: {max(times):.1f} 秒")
        
        # 性能提升计算
        old_time = 63.9  # 之前的用时
        speedup = old_time / avg_time
        print(f"\n🎯 性能提升：")
        print(f"  - 优化前: {old_time} 秒")
        print(f"  - 优化后: {avg_time:.1f} 秒")
        print(f"  - 提速: {speedup:.1f}x")
        print(f"  - 节省时间: {old_time - avg_time:.1f} 秒 ({(1 - avg_time/old_time)*100:.0f}%)")
        
        # 评估
        print("\n✅ 评估：")
        if avg_time < 10 and avg_products >= 145:
            print("  🎉 完美！速度快且获取了所有产品")
        elif avg_time < 15 and avg_products >= 140:
            print("  ✅ 优秀！速度和准确性都很好")
        elif avg_time < 20:
            print("  ✅ 良好！比之前快很多")
        else:
            print("  ⚠️ 还有优化空间")
            
    finally:
        browser_manager.shutdown()
        print("\n✅ 测试完成")


if __name__ == '__main__':
    test_speed_final() 