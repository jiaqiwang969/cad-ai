#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比test-06和当前分类器的差异
"""

import json
from collections import defaultdict

def load_test06_data():
    """加载test-06数据"""
    with open('results/traceparts_classification_tree_full.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['records']

def load_current_data():
    """加载当前分类器数据"""
    with open('results/cache/classification_tree_v20250604_001328.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 从树形结构中提取所有节点
    nodes = []
    def extract_nodes(node):
        if node.get('level', 0) > 1:  # 排除根节点
            nodes.append({
                'name': node['name'],
                'url': node['url'],
                'level': node['level'],
                'code': node['code']
            })
        for child in node.get('children', []):
            extract_nodes(child)
    
    if 'root' in data:
        extract_nodes(data['root'])
    
    return nodes

def extract_code_from_url(url):
    """从URL提取code"""
    if 'CatalogPath=TRACEPARTS%3A' in url:
        return url.split('CatalogPath=TRACEPARTS%3A')[1].split('&')[0]
    return url.split('/')[-1][:30]

def main():
    print("🔍 对比test-06和当前分类器的差异...")
    
    # 加载数据
    test06_records = load_test06_data()
    current_records = load_current_data()
    
    print(f"Test-06记录数: {len(test06_records)}")
    print(f"当前分类器记录数: {len(current_records)}")
    
    # 提取URL集合进行对比
    test06_urls = set(record['url'] for record in test06_records)
    current_urls = set(record['url'] for record in current_records)
    
    # 找出差异
    missing_in_current = test06_urls - current_urls
    extra_in_current = current_urls - test06_urls
    
    print(f"\n🔍 URL对比结果:")
    print(f"Test-06独有的URL: {len(missing_in_current)}")
    print(f"当前分类器独有的URL: {len(extra_in_current)}")
    
    if missing_in_current:
        print(f"\n❌ 当前分类器遗漏的URL:")
        for i, url in enumerate(sorted(missing_in_current)[:10]):  # 只显示前10个
            # 找到对应的记录
            record = next((r for r in test06_records if r['url'] == url), None)
            if record:
                print(f"  {i+1}. {record['name']} (Level {record['level']})")
                print(f"     URL: {url}")
        
        if len(missing_in_current) > 10:
            print(f"     ... 还有 {len(missing_in_current) - 10} 个遗漏的URL")
    
    if extra_in_current:
        print(f"\n➕ 当前分类器额外的URL:")
        for i, url in enumerate(sorted(extra_in_current)[:5]):  # 只显示前5个
            record = next((r for r in current_records if r['url'] == url), None)
            if record:
                print(f"  {i+1}. {record['name']} (Level {record['level']})")
                print(f"     URL: {url}")
    
    # 按层级统计差异
    test06_by_level = defaultdict(list)
    current_by_level = defaultdict(list)
    
    for record in test06_records:
        level = record['level']
        test06_by_level[level].append(record)
    
    for record in current_records:
        level = record['level']
        current_by_level[level].append(record)
    
    print(f"\n📊 按层级对比:")
    for level in sorted(set(list(test06_by_level.keys()) + list(current_by_level.keys()))):
        test06_count = len(test06_by_level[level])
        current_count = len(current_by_level[level])
        diff = current_count - test06_count
        
        status = "✅" if diff == 0 else "❌" if diff < 0 else "➕"
        print(f"  Level {level}: Test-06={test06_count}, 当前={current_count}, 差异={diff:+d} {status}")

if __name__ == "__main__":
    main()