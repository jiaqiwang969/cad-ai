#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示扩展缓存的使用
================
展示如何读取和使用包含产品链接的完整缓存
"""

import json
from pathlib import Path


def demo_extended_cache():
    """演示如何使用扩展后的缓存"""
    
    cache_file = Path('results/cache/classification_tree.json')
    
    if not cache_file.exists():
        print("❌ 缓存文件不存在，请先运行:")
        print("   1. python run_optimized_pipeline.py  # 生成基础分类树缓存")
        print("   2. python extend_cache.py            # 扩展缓存，添加产品链接")
        return
    
    # 加载缓存
    with open(cache_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 检查元数据
    metadata = data.get('metadata', {})
    version = metadata.get('version', '1.0')
    
    print(f"📂 缓存文件: {cache_file}")
    print(f"📊 缓存信息:")
    print(f"   • 版本: {version}")
    print(f"   • 生成时间: {metadata.get('generated', 'unknown')}")
    
    if 'with-products' in version:
        print(f"   • 扩展时间: {metadata.get('extended_at', 'unknown')}")
        print(f"   • 叶节点数: {metadata.get('total_leaves', 0)}")
        print(f"   • 产品总数: {metadata.get('total_products', 0)}")
        print("\n✅ 这是一个包含产品链接的完整缓存！")
    else:
        print("\n⚠️  这是一个基础缓存（仅包含分类树）")
        print("   运行 'python extend_cache.py' 来添加产品链接")
        return
    
    # 演示如何访问数据
    print("\n📋 数据结构示例:")
    
    # 1. 访问根节点
    root = data['root']
    print(f"\n1. 根节点: {root['name']} (code: {root['code']})")
    
    # 2. 访问叶节点列表
    leaves = data['leaves']
    print(f"\n2. 叶节点总数: {len(leaves)}")
    
    # 3. 展示前3个有产品的叶节点
    print("\n3. 前3个有产品的叶节点:")
    count = 0
    for leaf in leaves:
        if leaf.get('products') and count < 3:
            count += 1
            print(f"\n   叶节点 #{count}:")
            print(f"   • 名称: {leaf['name']}")
            print(f"   • 代码: {leaf['code']}")
            print(f"   • URL: {leaf['url']}")
            print(f"   • 产品数: {leaf.get('product_count', 0)}")
            print(f"   • 前3个产品链接:")
            for i, product_url in enumerate(leaf['products'][:3], 1):
                print(f"     {i}. {product_url[:80]}...")
    
    # 4. 递归遍历树结构示例
    print("\n4. 树结构遍历示例 (显示前2层):")
    def print_tree(node, level=0, max_level=2):
        if level > max_level:
            return
        
        indent = "   " * level
        is_leaf = node.get('is_leaf', False)
        product_count = node.get('product_count', 0)
        
        if is_leaf:
            print(f"{indent}├─ {node['name']} [叶节点, {product_count} 个产品]")
        else:
            print(f"{indent}├─ {node['name']}")
        
        for child in node.get('children', []):
            print_tree(child, level + 1, max_level)
    
    print_tree(root)
    
    print("\n💡 提示:")
    print("   • 使用 data['root'] 访问完整的树结构")
    print("   • 使用 data['leaves'] 快速访问所有叶节点")
    print("   • 每个叶节点的 'products' 字段包含该分类下的所有产品链接")
    print("   • 下次运行 run_optimized_pipeline.py 时将自动使用这个完整缓存")


if __name__ == '__main__':
    demo_extended_cache() 