#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试产品链接爬取功能"""

import sys
sys.path.append('.')

from src.crawler.ultimate_products import UltimateProductLinksCrawler
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

# 创建爬取器
crawler = UltimateProductLinksCrawler()

# 测试URL（使用迷你测试缓存中的一个叶节点）
test_url = "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-cartridge-blocks?CatalogPath=TRACEPARTS%3ATP01002002006"

print(f"\n测试URL: {test_url}\n")

# 爬取产品链接
products = crawler.extract_product_links(test_url)

print(f"\n结果: 爬取到 {len(products)} 个产品链接")
if products:
    print("\n前5个产品链接:")
    for i, link in enumerate(products[:5], 1):
        print(f"  {i}. {link[:100]}...")
else:
    print("\n未爬取到任何产品链接") 