#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终检查脚本
============
验证生产代码是否能正确获取145个产品
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def final_check():
    """最终检查"""
    test_url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("🎯 最终检查 - 生产代码测试")
    print("=" * 60)
    print(f"测试URL: {test_url}")
    print("期望: 145个产品")
    print("模式: 无头模式（生产环境）\n")
    
    # 创建爬取器
    browser_manager = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(browser_manager)
    
    try:
        print("⏳ 开始爬取...")
        start_time = time.time()
        
        products = crawler.extract_product_links(test_url)
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ 完成!")
        print(f"  获取产品数: {len(products)}")
        print(f"  期望产品数: 145")
        print(f"  完成率: {len(products)/145*100:.1f}%")
        print(f"  用时: {elapsed:.1f} 秒")
        print(f"  速度: {len(products)/elapsed:.1f} 个/秒")
        
        # 详细评估
        if len(products) == 145:
            print(f"\n🎉 完美！获取了所有产品")
            print("✅ 生产代码已准备就绪")
        elif len(products) >= 140:
            print(f"\n✅ 很好！获取了 {len(products)/145*100:.1f}% 的产品")
        elif len(products) >= 120:
            print(f"\n⚠️  还需优化！只获取了 {len(products)} 个产品")
        else:
            print(f"\n❌ 有问题！只获取了 {len(products)} 个产品")
            
        # 对比参考时间
        print(f"\n💡 参考:")
        print(f"  - test_debug_visual_smart.py: 7.1秒")
        print(f"  - test_5099_improved.py: 11.7秒（145产品）")
        
        if elapsed <= 15:
            print(f"  - 当前性能: 🎉 优秀")
        elif elapsed <= 30:
            print(f"  - 当前性能: ✅ 良好")
        else:
            print(f"  - 当前性能: ⚠️ 需要优化")
            
    finally:
        browser_manager.shutdown()
        print("\n✅ 测试完成")


if __name__ == '__main__':
    final_check() 