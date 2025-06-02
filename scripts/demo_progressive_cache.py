#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示渐进式缓存系统
================
展示三阶段缓存的结构和数据格式
"""

import json
from pathlib import Path
from datetime import datetime


def analyze_cache():
    """分析缓存文件并展示结构"""
    
    cache_file = Path('results/cache/classification_tree_full.json')
    
    if not cache_file.exists():
        print("❌ 缓存文件不存在，请先运行:")
        print("   python run_cache_manager.py")
        return
    
    # 加载缓存
    with open(cache_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 元数据
    metadata = data.get('metadata', {})
    
    print("📂 缓存文件分析")
    print("="*60)
    
    # 基本信息
    print(f"\n📊 缓存元数据:")
    print(f"   • 文件路径: {cache_file.resolve()}")
    print(f"   • 文件大小: {cache_file.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"   • 缓存级别: {metadata.get('cache_level_name', 'UNKNOWN')}")
    print(f"   • 版本: {metadata.get('version', 'unknown')}")
    print(f"   • 生成时间: {metadata.get('generated', 'unknown')}")
    
    # 计算缓存年龄
    if 'generated' in metadata:
        generated_time = datetime.fromisoformat(metadata['generated'])
        age_hours = (datetime.now() - generated_time).total_seconds() / 3600
        print(f"   • 缓存年龄: {age_hours:.1f} 小时")
    
    # 数据统计
    print(f"\n📈 数据统计:")
    print(f"   • 叶节点数: {metadata.get('total_leaves', 0):,}")
    print(f"   • 产品总数: {metadata.get('total_products', 0):,}")
    print(f"   • 规格总数: {metadata.get('total_specifications', 0):,}")
    
    # 根据缓存级别显示不同的信息
    cache_level = metadata.get('cache_level', 0)
    
    if cache_level >= 1:
        print(f"\n🌳 分类树结构 (Level 1):")
        show_classification_tree(data)
    
    if cache_level >= 2:
        print(f"\n📦 产品链接 (Level 2):")
        show_product_links(data)
    
    if cache_level >= 3:
        print(f"\n📋 产品规格 (Level 3):")
        show_specifications(data)
    
    # 缓存目录结构
    print(f"\n📁 缓存目录结构:")
    show_cache_directory()


def show_classification_tree(data):
    """展示分类树信息"""
    root = data.get('root', {})
    leaves = data.get('leaves', [])
    
    # 递归计算树的深度
    def get_depth(node, current=0):
        if not node.get('children'):
            return current
        return max(get_depth(child, current + 1) for child in node['children'])
    
    tree_depth = get_depth(root)
    
    print(f"   • 根节点: {root.get('name', 'Unknown')}")
    print(f"   • 树深度: {tree_depth} 层")
    print(f"   • 叶节点数: {len(leaves)}")
    
    # 显示前3个叶节点
    print(f"\n   前3个叶节点示例:")
    for i, leaf in enumerate(leaves[:3], 1):
        print(f"   {i}. {leaf['name']} (code: {leaf['code']})")


def show_product_links(data):
    """展示产品链接信息"""
    leaves = data.get('leaves', [])
    
    # 统计有产品的叶节点
    leaves_with_products = [l for l in leaves if l.get('product_count', 0) > 0]
    
    print(f"   • 有产品的叶节点: {len(leaves_with_products)}/{len(leaves)}")
    
    # 找出产品最多的叶节点
    if leaves_with_products:
        top_leaf = max(leaves_with_products, key=lambda x: x.get('product_count', 0))
        print(f"   • 产品最多的叶节点: {top_leaf['name']} ({top_leaf.get('product_count', 0)} 个产品)")
    
    # 显示产品链接示例
    print(f"\n   产品链接示例:")
    count = 0
    for leaf in leaves:
        if count >= 3:
            break
        products = leaf.get('products', [])
        if products:
            count += 1
            print(f"\n   叶节点: {leaf['name']}")
            # 产品可能是字符串或字典
            for j, product in enumerate(products[:2], 1):
                if isinstance(product, str):
                    print(f"     {j}. {product[:80]}...")
                else:
                    print(f"     {j}. {product.get('product_url', '')[:80]}...")


def show_specifications(data):
    """展示产品规格信息"""
    leaves = data.get('leaves', [])
    
    # 统计规格信息
    total_specs = 0
    products_with_specs = 0
    
    for leaf in leaves:
        for product in leaf.get('products', []):
            if isinstance(product, dict):
                specs = product.get('specifications', [])
                if specs:
                    products_with_specs += 1
                    total_specs += len(specs)
    
    print(f"   • 有规格的产品数: {products_with_specs}")
    print(f"   • 平均每产品规格数: {total_specs/products_with_specs if products_with_specs > 0 else 0:.1f}")
    
    # 显示规格示例
    print(f"\n   产品规格示例:")
    example_count = 0
    for leaf in leaves:
        if example_count >= 2:
            break
        for product in leaf.get('products', []):
            if example_count >= 2:
                break
            if isinstance(product, dict) and product.get('specifications'):
                example_count += 1
                print(f"\n   产品: {product['product_url'][:60]}...")
                print(f"   规格数: {product.get('spec_count', 0)}")
                for spec in product['specifications'][:3]:
                    print(f"     - {spec.get('reference', 'N/A')}: {spec.get('description', 'N/A')[:50]}...")


def show_cache_directory():
    """展示缓存目录结构"""
    cache_dir = Path('results/cache')
    
    if not cache_dir.exists():
        print("   缓存目录不存在")
        return
    
    # 统计文件
    product_files = list((cache_dir / 'products').glob('*.json')) if (cache_dir / 'products').exists() else []
    spec_files = list((cache_dir / 'specifications').glob('*.json')) if (cache_dir / 'specifications').exists() else []
    
    print(f"   results/cache/")
    print(f"   ├── classification_tree_full.json (主缓存文件)")
    if (cache_dir / 'classification_tree_full.json.bak').exists():
        print(f"   ├── classification_tree_full.json.bak (备份文件)")
    print(f"   ├── products/ ({len(product_files)} 个文件)")
    print(f"   └── specifications/ ({len(spec_files)} 个文件)")
    
    # 计算总大小
    total_size = 0
    for file in cache_dir.rglob('*.json'):
        total_size += file.stat().st_size
    
    print(f"\n   缓存总大小: {total_size / 1024 / 1024:.1f} MB")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 TraceParts 渐进式缓存系统演示")
    print("="*60)
    
    analyze_cache()
    
    print("\n" + "="*60)
    print("💡 使用提示:")
    print("="*60)
    print("\n1. 构建不同级别的缓存:")
    print("   python run_cache_manager.py --level classification  # 仅分类树")
    print("   python run_cache_manager.py --level products       # 分类树 + 产品链接")
    print("   python run_cache_manager.py --level specifications # 完整缓存")
    
    print("\n2. 使用优化流水线:")
    print("   python run_pipeline_v2.py                          # 使用缓存运行")
    print("   python run_pipeline_v2.py --no-cache               # 强制刷新")
    print("   python run_pipeline_v2.py --level products         # 只到产品级别")
    
    print("\n3. 导出数据:")
    print("   python run_pipeline_v2.py --output export.json     # 导出到文件")
    
    print("\n4. 管理缓存:")
    print("   rm -rf results/cache/products/                     # 清理产品缓存")
    print("   rm -rf results/cache/specifications/               # 清理规格缓存")
    print("   rm -rf results/cache/                              # 清理所有缓存")


if __name__ == '__main__':
    main() 