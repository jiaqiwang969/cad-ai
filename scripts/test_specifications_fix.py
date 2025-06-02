#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试修复后的规格爬取器"""

import sys
sys.path.append('.')

from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

# 创建爬取器
crawler = OptimizedSpecificationsCrawler()

# 测试URL（使用测试脚本中成功的产品）
test_url = "https://www.traceparts.cn/en/product/jw-winco-en-561-plastic-mounting-angle-brackets-type-b-and-c?CatalogPath=TRACEPARTS%3ATP05001&Product=90-05102020-040831"

print(f"\n测试URL: {test_url}\n")

# 爬取产品规格
result = crawler.extract_specifications(test_url)

print(f"\n结果:")
print(f"  成功: {result['success']}")
print(f"  规格数量: {result['count']}")
print(f"\n规格列表:")
for i, spec in enumerate(result['specifications'][:10], 1):
    print(f"  {i}. {spec['product_reference']} - {spec.get('description', '')}") 