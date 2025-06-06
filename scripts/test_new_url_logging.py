#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修改后的URL日志输出
===================
验证specifications_optimized.py中的日志现在是否显示完整URL
"""

import sys
sys.path.append('.')

from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)

print("\n" + "="*80)
print("🧪 测试修改后的URL日志输出")
print("="*80)

# 创建爬取器
crawler = OptimizedSpecificationsCrawler()

# 测试多个产品URL（包括成功和失败的情况）
test_urls = [
    # 成功案例：JW Winco产品
    "https://www.traceparts.cn/en/product/jw-winco-en-561-plastic-mounting-angle-brackets-type-b-and-c?CatalogPath=TRACEPARTS%3ATP05001&Product=90-05102020-040831",
    
    # 可能为0规格的案例
    "https://www.traceparts.cn/en/product/example-zero-specs-product",
    
    # 可能失败的案例（错误URL）
    "https://www.traceparts.cn/en/product/non-existent-product-url-test"
]

print(f"\n📋 测试 {len(test_urls)} 个产品URL的日志输出：")
print("   观察是否显示完整URL而非截断版本\n")

# 批量测试
result = crawler.extract_batch_specifications(test_urls, max_workers=3)

print(f"\n📊 测试结果汇总:")
print(f"   • 测试URL数量: {len(test_urls)}")
print(f"   • 成功数量: {result['summary']['success_cnt']}")
print(f"   • 失败数量: {len(test_urls) - result['summary']['success_cnt']}")
print(f"   • 总规格数: {result['summary']['total_specs']}")

print("\n✅ 测试完成！请检查上述日志是否显示完整的产品URL")
print("   应该看到类似以下格式的日志：")
print("   ✅ https://www.traceparts.cn/en/product/... -> X 规格")
print("   ⚠️  https://www.traceparts.cn/en/product/... -> 0 规格")
print("   ❌ https://www.traceparts.cn/en/product/... -> 提取失败: ...") 