#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试 - 获取所有145个产品
============================
测试改进后的爬虫是否能成功获取所有产品
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def test_final():
    """最终测试"""
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("🎯 最终测试 - 获取所有145个产品")
    print("=" * 80)
    print(f"URL: {url}")
    print("=" * 80)
    
    start_time = time.time()
    
    # 创建爬虫实例
    browser_manager = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(browser_manager)
    
    try:
        # 提取产品链接
        print("\n⏳ 开始提取产品...")
        products = crawler.extract_product_links(url)
        
        elapsed = time.time() - start_time
        
        # 结果统计
        print(f"\n✅ 提取完成！")
        print(f"  - 用时: {elapsed:.1f} 秒")
        print(f"  - 产品数: {len(products)}")
        print(f"  - 期望值: 145")
        print(f"  - 完成率: {len(products)/145*100:.1f}%")
        
        # 显示示例产品
        if products:
            print("\n📦 产品示例:")
            print("前3个:")
            for i, link in enumerate(products[:3], 1):
                print(f"  {i}. {link}")
            
            if len(products) > 6:
                print("\n后3个:")
                for i, link in enumerate(products[-3:], len(products)-2):
                    print(f"  {i}. {link}")
        
        # 评估结果
        print("\n📊 评估:")
        if len(products) >= 145:
            print("  🎉 完美！获取了所有产品")
        elif len(products) >= 140:
            print("  ✅ 优秀！获取了几乎所有产品")
        elif len(products) >= 120:
            print("  ✅ 良好！获取了大部分产品")
        elif len(products) >= 80:
            print("  ⚠️ 一般！只获取了部分产品")
        else:
            print("  ❌ 需要改进！产品数太少")
            
        # 保存结果
        if len(products) >= 120:
            import json
            output_file = "results/test_145_products.json"
            os.makedirs("results", exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'url': url,
                    'total': len(products),
                    'products': products,
                    'elapsed': elapsed
                }, f, indent=2, ensure_ascii=False)
            print(f"\n💾 结果已保存到: {output_file}")
            
    finally:
        browser_manager.shutdown()
        print("\n✅ 测试完成")


if __name__ == '__main__':
    test_final() 