#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试产品链接提取修复
==================
验证每个页面是否正确提取其实际的产品数量
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.crawler.ultimate_products import UltimateProductLinksCrawler

def test_different_pages():
    """测试不同页面的产品提取"""
    
    # 测试几个不同的叶节点URL（产品数量各不相同）
    test_urls = [
        # 这些是示例URL，实际应该从分类树中获取
        "https://www.traceparts.com/zh/product/bussmann-fusible-2ag-sfe-cartouche-6-3-x-32-mm-action-rapide?Product=10-01012018-091216",
        "https://www.traceparts.com/zh/product/wika-capteur-pression-type-s-20?Product=05-12072010-021831",
        # 可以添加更多测试URL
    ]
    
    crawler = UltimateProductLinksCrawler()
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{'='*60}")
        print(f"测试页面 {i}: {url}")
        print(f"{'='*60}")
        
        links = crawler.extract_product_links(url)
        
        print(f"\n✅ 结果：")
        print(f"  - 提取到 {len(links)} 个产品链接")
        print(f"  - 前5个链接:")
        for j, link in enumerate(links[:5], 1):
            print(f"    {j}. {link[:100]}...")
        
        if len(links) > 5:
            print(f"  - ... 还有 {len(links)-5} 个链接")

if __name__ == "__main__":
    print("开始测试产品链接提取修复...")
    test_different_pages() 