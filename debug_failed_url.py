#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试失败URL的页面结构
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler

def debug_failed_url():
    """调试失败的URL"""
    
    # 失败的URL示例
    failed_url = "https://www.traceparts.cn/en/product/item-industrietechnik-gmbh-stairway-assembly-set-pp-30deg?CatalogPath=TRACEPARTS%3ATP12002018002&Product=30-12112020-084493"
    
    # 成功的URL对比
    success_url = "https://www.traceparts.cn/en/product/apostoli-f30?CatalogPath=TRACEPARTS%3ATP12002018003004&Product=90-23112023-059945"
    
    crawler = OptimizedSpecificationsCrawler()
    
    print("🧪 调试失败URL的页面结构")
    print("="*60)
    
    # 测试失败的URL
    print(f"\n❌ 测试失败URL:")
    print(f"   {failed_url}")
    
    result1 = crawler.extract_specifications(failed_url)
    print(f"   结果: 成功={result1['success']}, 规格数={result1['count']}")
    
    if not result1['success']:
        print(f"   错误: {result1.get('error', 'Unknown')}")
    
    time.sleep(2)
    
    # 测试成功的URL
    print(f"\n✅ 测试成功URL:")
    print(f"   {success_url}")
    
    result2 = crawler.extract_specifications(success_url)
    print(f"   结果: 成功={result2['success']}, 规格数={result2['count']}")
    
    if not result2['success']:
        print(f"   错误: {result2.get('error', 'Unknown')}")
    
    # 对比分析
    print(f"\n📊 对比分析:")
    print(f"   失败URL供应商: item-industrietechnik-gmbh")
    print(f"   成功URL供应商: apostoli")
    print(f"   页面结构可能存在差异")

if __name__ == '__main__':
    debug_failed_url()