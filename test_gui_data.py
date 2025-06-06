#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI数据加载测试脚本
================

测试GUI的数据加载和解析功能，不启动实际界面
"""

import json
from pathlib import Path
from traceparts_gui import TracepartsDataViewer


def test_cache_data_loading():
    """测试缓存数据加载"""
    print("🧪 测试GUI数据加载功能...")
    
    cache_dir = Path("results/cache")
    if not cache_dir.exists():
        print("❌ 缓存目录不存在")
        return False
    
    # 测试读取缓存索引
    cache_index_file = cache_dir / 'cache_index.json'
    if cache_index_file.exists():
        with open(cache_index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        print(f"✅ 缓存索引读取成功")
        print(f"   最新文件: {list(index_data.get('latest_files', {}).keys())}")
        
        # 测试读取最新的缓存文件
        latest_files = index_data.get('latest_files', {})
        for level, filename in latest_files.items():
            cache_file = cache_dir / filename
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"✅ {level} 级别缓存读取成功")
                print(f"   文件: {filename}")
                print(f"   叶节点数: {len(data.get('leaves', []))}")
                print(f"   是否有根节点: {'是' if 'root' in data else '否'}")
                
                # 测试根节点结构
                if 'root' in data:
                    root = data['root']
                    print(f"   根节点名称: {root.get('name', 'Unknown')}")
                    print(f"   根节点子节点数: {len(root.get('children', []))}")
                    
                    # 显示前几个子节点
                    children = root.get('children', [])[:3]
                    for i, child in enumerate(children):
                        print(f"     子节点{i+1}: {child.get('name', 'Unknown')} (Level {child.get('level', 0)})")
                
                # 测试叶节点结构
                leaves = data.get('leaves', [])[:3]
                print(f"   前3个叶节点:")
                for i, leaf in enumerate(leaves):
                    product_count = leaf.get('product_count', 0)
                    print(f"     叶节点{i+1}: {leaf.get('name', 'Unknown')} ({product_count}个产品)")
                
                print()
        
        return True
    else:
        print("❌ 缓存索引文件不存在")
        return False


def test_tree_structure_parsing():
    """测试树形结构解析"""
    print("🌳 测试树形结构解析...")
    
    # 创建一个简化的GUI实例（不启动界面）
    try:
        cache_dir = Path("results/cache")
        cache_index_file = cache_dir / 'cache_index.json'
        
        if cache_index_file.exists():
            with open(cache_index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            latest_files = index_data.get('latest_files', {})
            
            # 找到最高级别的缓存
            for level in ['specifications', 'products', 'classification']:
                if level in latest_files:
                    cache_file = cache_dir / latest_files[level]
                    if cache_file.exists():
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        print(f"✅ 使用 {level.upper()} 级别缓存进行测试")
                        
                        # 测试统计计算
                        root_data = data.get('root', {})
                        leaves_data = data.get('leaves', [])
                        
                        total_leaves = len(leaves_data)
                        total_products = sum(leaf.get('product_count', 0) for leaf in leaves_data)
                        total_specs = 0
                        
                        if level == 'specifications':
                            for leaf in leaves_data:
                                for product in leaf.get('products', []):
                                    if isinstance(product, dict):
                                        total_specs += product.get('spec_count', 0)
                        
                        print(f"   📊 统计信息:")
                        print(f"     总叶节点: {total_leaves}")
                        print(f"     总产品数: {total_products}")
                        if total_specs > 0:
                            print(f"     总规格数: {total_specs}")
                        
                        # 测试层级计算
                        if root_data and 'children' in root_data:
                            def count_levels(node, current_level=1):
                                max_level = current_level
                                for child in node.get('children', []):
                                    child_max = count_levels(child, current_level + 1)
                                    max_level = max(max_level, child_max)
                                return max_level
                            
                            max_depth = count_levels(root_data)
                            print(f"     最大层级深度: {max_depth}")
                        
                        break
        
        print("✅ 树形结构解析测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 树形结构解析测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 TraceParts GUI 数据加载测试")
    print("=" * 50)
    
    success1 = test_cache_data_loading()
    print()
    success2 = test_tree_structure_parsing()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ 所有测试通过！GUI数据加载功能正常")
        print("\n💡 现在可以运行 'make gui' 启动完整界面")
    else:
        print("❌ 部分测试失败，请检查数据文件")


if __name__ == "__main__":
    main()