#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试叶节点检测的修复效果
"""

import sys
import logging
from pathlib import Path
import re

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

def test_regex_patterns():
    """测试正则表达式匹配模式"""
    print("🧪 测试正则表达式匹配...")
    
    # 测试文本样例
    test_cases = [
        ("98 results found", True),   # 应该匹配
        ("2,569 results", True),      # 应该匹配
        ("1234 results", True),       # 应该匹配
        ("search results", False),    # 不应该匹配
        ("filter results", False),    # 不应该匹配
        ("results page", False),      # 不应该匹配
        ("showing 42 results", False), # 应该被排除
        ("found 123 results", False),  # 应该被排除
        ("123products found", False),  # 不应该匹配（没有空格）
        ("0 results", True),          # 应该匹配
    ]
    
    # 修正的正则
    basic_pattern = r'\b\d{1,3}(?:,\d{3})*\s+results?\b|\b\d{4,}\s+results?\b'
    
    # 干扰词模式
    interference_patterns = [
        r'search\s+\d+\s+results',
        r'filter\s+\d+\s+results', 
        r'found\s+\d+\s+results',
        r'showing\s+\d+\s+results'
    ]
    
    print("测试基本正则匹配:")
    for text, expected in test_cases:
        print(f"\n--- 测试: '{text}' ---")
        
        # 基本正则匹配
        basic_match_obj = re.search(basic_pattern, text, re.IGNORECASE)
        basic_match = bool(basic_match_obj)
        if basic_match_obj:
            print(f"  🔍 基本正则匹配到: '{basic_match_obj.group()}'")
        else:
            print(f"  ❌ 基本正则未匹配")
        
        # 检查干扰词
        has_interference = False
        matched_interference = None
        if basic_match:
            for pattern in interference_patterns:
                interference_match = re.search(pattern, text, re.IGNORECASE)
                if interference_match:
                    has_interference = True
                    matched_interference = interference_match.group()
                    print(f"  ⚠️ 发现干扰词: '{matched_interference}' (模式: {pattern})")
                    break
            if not has_interference:
                print(f"  ✅ 未发现干扰词")
        
        # 最终结果
        final_result = basic_match and not has_interference
        status = "✅" if final_result == expected else "❌"
        
        print(f"  {status} 最终结果: {final_result}, 期望: {expected}")
        if final_result != expected:
            print(f"      ❗ 结果不符合期望！")

def test_classification_levels():
    """测试分类层级筛选"""
    print("\n🧪 测试分类层级筛选...")
    
    # 模拟节点数据
    test_nodes = [
        {"name": "Root", "level": 1, "children": []},
        {"name": "Category", "level": 2, "children": []},
        {"name": "Subcategory", "level": 3, "children": []},
        {"name": "LeafCandidate1", "level": 4, "children": []},  # 应该被选中
        {"name": "LeafCandidate2", "level": 5, "children": []},  # 应该被选中
        {"name": "HasChildren", "level": 4, "children": [{"name": "child"}]},  # 不应该被选中
        {"name": "TooShallow", "level": 3, "children": []},  # 不应该被选中
    ]
    
    print("使用新的筛选条件 (level >= 4 AND no children):")
    potential_leaves = []
    
    for node in test_nodes:
        has_no_children = len(node.get('children', [])) == 0
        is_deep_enough = node['level'] >= 4
        
        if has_no_children and is_deep_enough:
            potential_leaves.append(node)
            print(f"  ✅ {node['name']} (L{node['level']}) - 潜在叶节点")
        else:
            print(f"  ❌ {node['name']} (L{node['level']}) - 跳过 (children:{not has_no_children}, shallow:{not is_deep_enough})")
    
    print(f"\n筛选结果: {len(potential_leaves)}/{len(test_nodes)} 个节点被标记为潜在叶节点")

def test_real_url_patterns():
    """测试真实URL的检测逻辑"""
    print("\n🧪 测试真实URL检测逻辑...")
    
    # 模拟一些真实的页面内容
    test_pages = [
        {
            "name": "真实产品页面",
            "content": "Found 142 results for pneumatic cylinders. Sort by: Name, Price",
            "has_product_links": True,
            "expected": True
        },
        {
            "name": "空分类页面", 
            "content": "Search results for category. No products found.",
            "has_product_links": False,
            "expected": False
        },
        {
            "name": "包含干扰词的页面",
            "content": "Showing 25 results in search results page",
            "has_product_links": False,
            "expected": False
        },
        {
            "name": "大数字产品页面",
            "content": "Total: 1,234 results available. Sort by relevance.",
            "has_product_links": True,
            "expected": True
        },
        {
            "name": "零结果页面",
            "content": "0 results found for your search. Try different keywords.",
            "has_product_links": False,
            "expected": False
        }
    ]
    
    # 正则模式（和代码中一致）
    basic_pattern = r'\b\d{1,3}(?:,\d{3})*\s+results?\b|\b\d{4,}\s+results?\b'
    interference_patterns = [
        r'search\s+\d+\s+results',
        r'filter\s+\d+\s+results', 
        r'found\s+\d+\s+results',
        r'showing\s+\d+\s+results'
    ]
    
    for page in test_pages:
        print(f"\n--- {page['name']} ---")
        print(f"内容: '{page['content']}'")
        
        # 检测数字+results
        basic_match = bool(re.search(basic_pattern, page['content'], re.IGNORECASE))
        print(f"数字+results匹配: {basic_match}")
        
        # 检查0结果和干扰词
        has_interference = False
        if basic_match:
            # 先检查0结果
            if re.search(r'\b0\s+results?\b', page['content'], re.IGNORECASE):
                has_interference = True
                print(f"发现0结果，排除")
            else:
                # 再检查其他干扰词
                for pattern in interference_patterns:
                    if re.search(pattern, page['content'], re.IGNORECASE):
                        has_interference = True
                        print(f"发现干扰词: {pattern}")
                        break
        
        # 产品链接检查
        has_product_links = page['has_product_links']
        print(f"产品链接: {has_product_links}")
        
        # 最终判断（和代码逻辑一致）
        has_numbered_results = basic_match and not has_interference
        is_leaf = has_numbered_results or has_product_links
        
        status = "✅" if is_leaf == page['expected'] else "❌"
        print(f"{status} 最终判断: {is_leaf}, 期望: {page['expected']}")

if __name__ == "__main__":
    test_regex_patterns()
    test_classification_levels()
    test_real_url_patterns()
    print("\n🧪 快速测试完成")