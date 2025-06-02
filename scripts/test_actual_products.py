#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试缓存中实际产品的规格提取"""

import sys
sys.path.append('.')

from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

# 创建爬取器
crawler = OptimizedSpecificationsCrawler()

# 读取产品缓存
with open('results/cache/products/TP01002002006.json', 'r') as f:
    products = json.load(f)

print(f"找到 {len(products)} 个产品链接")
print("\n测试前5个产品:")

# 测试前5个产品
for i, product_url in enumerate(products[:5], 1):
    print(f"\n[{i}/5] 测试产品:")
    print(f"  URL: {product_url[:100]}...")
    
    result = crawler.extract_specifications(product_url)
    
    print(f"  成功: {result['success']}")
    print(f"  规格数量: {result['count']}")
    
    if result['specifications']:
        print(f"  前3个规格:")
        for j, spec in enumerate(result['specifications'][:3], 1):
            print(f"    {j}. {spec['product_reference']}") 