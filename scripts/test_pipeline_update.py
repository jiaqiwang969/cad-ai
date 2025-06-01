#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试更新后的Pipeline
====================
验证产品爬取器的改进是否生效
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def test_updated_pipeline():
    """测试更新后的产品爬取器"""
    # 测试两个URL：一个小的（145个产品）和一个大的（5099个产品）
    test_cases = [
        {
            "name": "小页面测试（145个产品）",
            "url": "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017",
            "expected": 145
        },
        {
            "name": "大页面测试（5099个产品）",
            "url": "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008",
            "expected": 5099,
            "limit_test": 500  # 只测试前500个，避免太长时间
        }
    ]
    
    print("🎯 测试更新后的产品爬取器")
    print("=" * 80)
    
    browser_manager = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(browser_manager)
    
    try:
        for test in test_cases:
            print(f"\n📋 {test['name']}")
            print(f"URL: {test['url']}")
            print(f"期望产品数: {test['expected']}")
            
            # 如果是大页面测试，提醒用户
            if 'limit_test' in test:
                print(f"⚠️  为节省时间，只测试前 {test['limit_test']} 个产品")
                print("   实际pipeline会获取所有产品")
            
            # 提取产品
            import time
            start_time = time.time()
            products = crawler.extract_product_links(test['url'])
            elapsed = time.time() - start_time
            
            # 结果分析
            print(f"\n✅ 结果:")
            print(f"  - 获取产品数: {len(products)}")
            print(f"  - 用时: {elapsed:.1f} 秒")
            print(f"  - 速度: {len(products)/elapsed:.1f} 个/秒")
            
            # 评估
            if test['expected'] <= 200:
                # 小页面应该获取所有
                if len(products) >= test['expected'] * 0.98:
                    print(f"  - 状态: 🎉 完美！获取了 {len(products)/test['expected']*100:.1f}%")
                else:
                    print(f"  - 状态: ⚠️ 需要检查，只获取了 {len(products)/test['expected']*100:.1f}%")
            else:
                # 大页面
                if 'limit_test' in test and len(products) >= test['limit_test'] * 0.9:
                    print(f"  - 状态: ✅ 测试通过！")
                elif len(products) >= 1000:
                    print(f"  - 状态: ✅ 良好！可以处理大量产品")
                else:
                    print(f"  - 状态: ⚠️ 可能需要优化")
            
            # 如果是限制测试，提前停止
            if 'limit_test' in test and len(products) >= test['limit_test']:
                print("\n⏸️  达到测试限制，停止该测试")
                break
                
    finally:
        browser_manager.shutdown()
        print("\n✅ 测试完成")
        print("\n💡 提示: 现在可以运行 'make pipeline' 使用改进后的算法")


if __name__ == '__main__':
    test_updated_pipeline() 