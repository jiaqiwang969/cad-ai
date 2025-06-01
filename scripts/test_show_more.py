#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Show More Results按钮
========================
专门测试点击"Show More Results"按钮加载所有产品
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def test_show_more():
    """测试Show More功能"""
    # 目标URL - 有145个产品的页面
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("🎯 测试 Show More Results 功能")
    print("=" * 80)
    print(f"URL: {url}")
    print("期望产品数: 145")
    print("=" * 80)
    
    # 创建爬虫实例
    browser_manager = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(browser_manager)
    
    try:
        # 提取产品链接
        print("\n开始提取产品...")
        products = crawler.extract_product_links(url)
        
        print(f"\n✅ 成功提取 {len(products)} 个产品")
        
        # 显示前5个和后5个产品
        if products:
            print("\n前5个产品:")
            for i, link in enumerate(products[:5], 1):
                print(f"  {i}. {link}")
            
            if len(products) > 10:
                print("\n后5个产品:")
                for i, link in enumerate(products[-5:], len(products)-4):
                    print(f"  {i}. {link}")
        
        # 分析结果
        print(f"\n📊 分析:")
        print(f"  - 提取到: {len(products)} 个产品")
        print(f"  - 期望值: 145 个产品")
        print(f"  - 完成率: {len(products)/145*100:.1f}%")
        
        if len(products) >= 140:
            print("\n🎉 成功！已获取几乎所有产品")
        elif len(products) > 80:
            print("\n✅ 有进步！成功点击了Show More按钮")
        else:
            print("\n⚠️ 仍需改进，只获取到初始的80个产品")
            
    finally:
        browser_manager.shutdown()


if __name__ == '__main__':
    test_show_more() 