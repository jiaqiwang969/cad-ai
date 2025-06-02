#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试Timken产品的规格提取"""

import sys
sys.path.append('.')

from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

# 创建爬取器
crawler = OptimizedSpecificationsCrawler()

# 测试Timken产品（与测试脚本中的默认URL相同）
test_url = "https://www.traceparts.cn/en/product/the-timken-company-double-concentric-cartridge-block-qaamc10a050s?CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175"

print(f"\n测试URL: {test_url}\n")

# 爬取产品规格
result = crawler.extract_specifications(test_url)

print(f"\n结果:")
print(f"  成功: {result['success']}")
print(f"  规格数量: {result['count']}")

if result['specifications']:
    print(f"\n规格列表:")
    for i, spec in enumerate(result['specifications'][:10], 1):
        print(f"  {i}. {spec['product_reference']}")
        if spec.get('dimensions'):
            print(f"     尺寸: {spec['dimensions']}")
        if spec.get('weight'):
            print(f"     重量: {spec['weight']}")
else:
    print("\n未提取到任何规格") 