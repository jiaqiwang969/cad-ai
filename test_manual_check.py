#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动检查页面内容
"""

import requests
import re

def manual_check():
    """手动检查页面内容"""
    
    test_url = "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-pillow-block-bearings?CatalogPath=TRACEPARTS%3ATP01002002003&PageSize=100"
    
    print("🔍 手动检查页面内容...")
    print(f"📍 URL: {test_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        print("\n📡 使用requests获取页面...")
        response = requests.get(test_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        page_text = response.text
        print(f"📄 页面大小: {len(page_text)} 字符")
        
        # 检查关键模式
        print("\n🔍 检查关键模式:")
        
        # 1. 检查数字+results
        results_matches = re.findall(r'\b\d{1,3}(?:,\d{3})*\s+results?\b|\b\d{4,}\s+results?\b', page_text, re.IGNORECASE)
        print(f"   • 数字+results 匹配: {results_matches}")
        
        # 2. 检查Product链接
        product_count = page_text.count('&Product=')
        print(f"   • Product链接数量: {product_count}")
        
        # 3. 检查Sort by
        has_sort_by = 'Sort by' in page_text
        print(f"   • Sort by: {has_sort_by}")
        
        # 4. 查找一些关键字段
        print(f"\n📊 关键字段检查:")
        print(f"   • 'results' 出现次数: {page_text.lower().count('results')}")
        print(f"   • 'product' 出现次数: {page_text.lower().count('product')}")
        print(f"   • '0 results': {'是' if '0 results' in page_text.lower() else '否'}")
        
        # 5. 检查分类链接
        classification_links = page_text.count('traceparts-classification-')
        print(f"   • 分类链接数量: {classification_links}")
        
        # 6. 查找分类链接片段
        if classification_links > 0:
            print(f"\n📝 分类链接片段:")
            classification_matches = re.findall(r'href="[^"]*traceparts-classification-[^"]*"', page_text)
            for i, match in enumerate(classification_matches[:5]):  # 只显示前5个
                print(f"   {i+1}: {match}")
        
        # 7. 查看页面片段
        if 'results' in page_text.lower():
            print(f"\n📝 包含'results'的片段:")
            lines = page_text.split('\n')
            for i, line in enumerate(lines):
                if 'results' in line.lower():
                    print(f"   行{i}: {line.strip()[:100]}...")
                    if i > 3:  # 只显示前几个
                        break
        
        # 最终判断
        has_numbered_results = bool(results_matches) and not re.search(r'\b0\s+results?\b', page_text, re.IGNORECASE)
        has_product_links = product_count > 0
        is_leaf = has_numbered_results or has_product_links
        
        print(f"\n📊 最终判断:")
        print(f"   • 有效数字结果: {has_numbered_results}")
        print(f"   • 有产品链接: {has_product_links}")
        print(f"   • 是叶节点: {'✅ 是' if is_leaf else '❌ 否'}")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")

if __name__ == "__main__":
    manual_check()