#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试优化后的速度
================
验证产品爬取器的速度是否接近test_5099_improved.py
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def test_speed():
    """测试优化后的速度"""
    # 使用145产品的页面进行快速测试
    test_url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("🚀 测试优化后的产品爬取速度")
    print("=" * 60)
    print(f"测试URL: {test_url}")
    print("目标: 145个产品\n")
    
    # 创建爬取器
    browser_manager = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(browser_manager)
    
    try:
        # 运行3次测试
        times = []
        for i in range(3):
            print(f"\n第 {i+1} 次测试...")
            start_time = time.time()
            
            products = crawler.extract_product_links(test_url)
            
            elapsed = time.time() - start_time
            times.append(elapsed)
            
            print(f"  ✓ 获取 {len(products)} 个产品")
            print(f"  ✓ 用时 {elapsed:.1f} 秒")
            print(f"  ✓ 速度 {len(products)/elapsed:.1f} 个/秒")
            
            # 短暂休息
            if i < 2:
                time.sleep(2)
        
        # 计算平均值
        avg_time = sum(times) / len(times)
        print(f"\n{'='*60}")
        print(f"📊 统计结果:")
        print(f"  - 平均用时: {avg_time:.1f} 秒")
        print(f"  - 最快: {min(times):.1f} 秒")
        print(f"  - 最慢: {max(times):.1f} 秒")
        
        # 与test_5099_improved.py的11.7秒对比
        print(f"\n💡 参考: test_5099_improved.py 用时 11.7 秒")
        if avg_time <= 15:
            print("🎉 优秀！速度非常接近最优实现")
        elif avg_time <= 20:
            print("✅ 不错！速度在可接受范围内")
        else:
            print("⚠️  可能还需要进一步优化")
            
    finally:
        browser_manager.shutdown()
        print("\n✅ 测试完成")


if __name__ == '__main__':
    test_speed() 