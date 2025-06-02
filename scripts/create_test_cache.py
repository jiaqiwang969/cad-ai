#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建测试用的缓存文件
==================
生成一个简化但格式正确的classification_tree.json
"""

import json
from pathlib import Path


def extract_leaves(node, leaves=None):
    """递归提取所有叶节点"""
    if leaves is None:
        leaves = []
    
    if node.get('is_leaf', False) or not node.get('children'):
        # 这是叶节点
        leaf = {
            'name': node['name'],
            'url': node['url'],
            'level': node['level'],
            'code': node['code'],
            'is_leaf': True
        }
        leaves.append(leaf)
    else:
        # 递归处理子节点
        for child in node.get('children', []):
            extract_leaves(child, leaves)
    
    return leaves


def create_test_cache():
    """创建测试缓存文件"""
    
    # 定义树结构
    root = {
        "name": "TraceParts Classification",
        "url": "https://www.traceparts.cn/en/search/traceparts-classification?CatalogPath=TRACEPARTS%3ATRACEPARTS",
        "level": 1,
        "code": "TRACEPARTS_ROOT",
        "children": [
            {
                "name": "Building & Constructions (materials and equipments)",
                "url": "https://www.traceparts.cn/en/search/traceparts-classification-building-constructions-materials-and-equipments?CatalogPath=TRACEPARTS%3ATP12",
                "level": 2,
                "code": "TP12",
                "children": [
                    {
                        "name": "Buildings",
                        "url": "https://www.traceparts.cn/en/search/traceparts-classification-building-constructions-materials-and-equipments-buildings?CatalogPath=TRACEPARTS%3ATP12001",
                        "level": 3,
                        "code": "TP12001",
                        "children": [
                            {
                                "name": "Mobile offices",
                                "url": "https://www.traceparts.cn/en/search/traceparts-classification-building-constructions-materials-and-equipments-buildings-mobile-offices?CatalogPath=TRACEPARTS%3ATP12001001",
                                "level": 4,
                                "code": "TP12001001",
                                "children": [],
                                "is_leaf": True
                            },
                            {
                                "name": "Solar greenhouses",
                                "url": "https://www.traceparts.cn/en/search/traceparts-classification-building-constructions-materials-and-equipments-buildings-solar-greenhouses?CatalogPath=TRACEPARTS%3ATP12001002",
                                "level": 4,
                                "code": "TP12001002",
                                "children": [],
                                "is_leaf": True
                            },
                            {
                                "name": "Storage buildings",
                                "url": "https://www.traceparts.cn/en/search/traceparts-classification-building-constructions-materials-and-equipments-buildings-storage-buildings?CatalogPath=TRACEPARTS%3ATP12001003",
                                "level": 4,
                                "code": "TP12001003",
                                "children": [],
                                "is_leaf": True
                            }
                        ],
                        "is_leaf": False
                    }
                ],
                "is_leaf": False
            }
        ],
        "is_leaf": False
    }
    
    # 提取所有叶节点
    leaves = extract_leaves(root)
    
    # 创建完整的缓存数据
    cache_data = {
        "root": root,
        "leaves": leaves
    }
    
    # 保存到文件
    cache_file = Path('results/cache/classification_tree.json')
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 测试缓存文件已创建: {cache_file}")
    print(f"   • 根节点: {root['name']}")
    print(f"   • 叶节点数: {len(leaves)}")
    print(f"   • 叶节点列表:")
    for leaf in leaves:
        print(f"     - {leaf['name']} ({leaf['code']})")
    
    return cache_data


if __name__ == '__main__':
    create_test_cache() 