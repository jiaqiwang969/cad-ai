#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 pipeline_v2 中的规格提取功能"""

import sys
sys.path.append('.')

from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

# 创建爬取器
crawler = OptimizedSpecificationsCrawler()

# 测试多个不同类型的产品
test_products = [
    {
        'name': 'JW Winco (多规格横向表格)',
        'url': 'https://www.traceparts.cn/en/product/jw-winco-en-561-plastic-mounting-angle-brackets-type-b-and-c?CatalogPath=TRACEPARTS%3ATP05001&Product=90-05102020-040831'
    },
    {
        'name': 'Timken (多产品编号列)',
        'url': 'https://www.traceparts.cn/en/product/the-timken-company-double-concentric-cartridge-block-qaamc10a050s?CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175'
    },
    {
        'name': 'Petzoldt德语产品',
        'url': 'https://www.traceparts.cn/en/product/petzoldt-cpleuchten-gmbh-rohrleuchte-sls50-14w-230v?CatalogPath=TRACEPARTS%3ATP12001003&Product=90-13052019-057778'
    }
]

print("\n" + "="*80)
print("🧪 测试 Pipeline V2 规格提取功能")
print("="*80)

total_specs = 0
success_count = 0

for i, product in enumerate(test_products, 1):
    print(f"\n[{i}/{len(test_products)}] 测试产品: {product['name']}")
    print(f"  URL: {product['url'][:80]}...")
    
    result = crawler.extract_specifications(product['url'])
    
    print(f"  成功: {result['success']}")
    print(f"  规格数量: {result['count']}")
    
    if result['success']:
        success_count += 1
        total_specs += result['count']
        
        # 显示前3个规格
        if result['specifications']:
            print(f"  前3个规格:")
            for j, spec in enumerate(result['specifications'][:3], 1):
                print(f"    {j}. {spec['product_reference']}")
                if spec.get('dimensions'):
                    print(f"       尺寸: {spec['dimensions']}")
                if spec.get('table_type'):
                    print(f"       表格类型: {spec['table_type']}")
    else:
        print(f"  错误: {result.get('error', 'unknown')}")

print("\n" + "="*80)
print("📊 测试汇总")
print("="*80)
print(f"✅ 成功: {success_count}/{len(test_products)} 个产品")
print(f"📋 总规格数: {total_specs}")
print(f"📈 平均每个产品: {total_specs/len(test_products):.1f} 个规格")
print("="*80) 