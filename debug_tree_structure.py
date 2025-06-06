#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试树形结构构建问题
"""

import json
import sys
sys.path.append('/Users/jqwang/50-爬虫01')
from src.crawler.classification_optimized import OptimizedClassificationCrawler

def analyze_tree_structure():
    """分析树形结构问题"""
    
    # 加载test-06数据
    with open('results/traceparts_classification_tree_full.json', 'r', encoding='utf-8') as f:
        test06_data = json.load(f)
    
    # 转换格式
    records = [{'name': r['name'], 'url': r['url']} for r in test06_data['records']]
    print(f"📊 Test-06总记录数: {len(records)}")
    
    # 使用修复后的分类器构建树
    crawler = OptimizedClassificationCrawler()
    root, leaves = crawler.build_classification_tree(records)
    
    print(f"🌳 构建的叶节点数: {len(leaves)}")
    print(f"📉 差异: {len(records) - len(leaves)}")
    
    # 分析树中的所有节点
    all_nodes = []
    def collect_nodes(node):
        if node.get('level', 0) > 1:  # 排除根节点
            all_nodes.append(node)
        for child in node.get('children', []):
            collect_nodes(child)
    
    collect_nodes(root)
    print(f"🔢 树中总节点数: {len(all_nodes)}")
    
    # 统计叶节点和非叶节点
    leaf_nodes = [n for n in all_nodes if n.get('is_leaf', False)]
    non_leaf_nodes = [n for n in all_nodes if not n.get('is_leaf', False)]
    
    print(f"🌿 叶节点数: {len(leaf_nodes)}")
    print(f"🏗️ 非叶节点数: {len(non_leaf_nodes)}")
    
    # 找出test-06中存在但在树中变成非叶节点的记录
    test06_urls = set(r['url'] for r in records)
    tree_leaf_urls = set(n['url'] for n in leaf_nodes)
    tree_non_leaf_urls = set(n['url'] for n in non_leaf_nodes)
    
    # 在test-06中是记录，但在树中变成了非叶节点
    became_non_leaf = test06_urls & tree_non_leaf_urls
    print(f"\n📋 在test-06中存在，但在树中变成非叶节点的URL数: {len(became_non_leaf)}")
    
    if became_non_leaf:
        print("前10个变成非叶节点的例子:")
        for i, url in enumerate(sorted(became_non_leaf)[:10]):
            # 找到对应的节点
            node = next((n for n in non_leaf_nodes if n['url'] == url), None)
            if node:
                child_count = len(node.get('children', []))
                print(f"  {i+1}. {node['name'][:50]}... (Level {node['level']}, {child_count} 子节点)")
                print(f"     Code: {node['code']}")
    
    # 检查是否有重复的code
    codes = [n['code'] for n in all_nodes]
    duplicate_codes = set([code for code in codes if codes.count(code) > 1])
    if duplicate_codes:
        print(f"\n⚠️  发现重复的code: {len(duplicate_codes)}")
        for code in sorted(duplicate_codes)[:5]:
            nodes_with_code = [n for n in all_nodes if n['code'] == code]
            print(f"  Code '{code}' 出现 {len(nodes_with_code)} 次:")
            for node in nodes_with_code:
                print(f"    - {node['name'][:30]}... (Level {node['level']})")
    
    return root, leaves, all_nodes

if __name__ == "__main__":
    analyze_tree_structure()