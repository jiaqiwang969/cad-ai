#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建Pipeline V2测试用的缓存文件
================================
生成一个适用于渐进式缓存系统的第一级缓存文件
"""

import json
from pathlib import Path
from datetime import datetime


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


def create_test_cache_v2():
    """创建Pipeline V2测试缓存文件"""
    
    # 定义树结构（更丰富的测试数据）
    root = {
        "name": "TraceParts Classification",
        "url": "https://www.traceparts.cn/en/search/traceparts-classification?CatalogPath=TRACEPARTS%3ATRACEPARTS",
        "level": 1,
        "code": "TRACEPARTS_ROOT",
        "is_leaf": False,
        "children": [
            {
                "name": "Mechanical components",
                "url": "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components?CatalogPath=TRACEPARTS%3ATP01",
                "level": 2,
                "code": "TP01",
                "is_leaf": False,
                "children": [
                    {
                        "name": "Bearings",
                        "url": "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings?CatalogPath=TRACEPARTS%3ATP01002",
                        "level": 3,
                        "code": "TP01002",
                        "is_leaf": False,
                        "children": [
                            {
                                "name": "Ball bearings",
                                "url": "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-ball-bearings?CatalogPath=TRACEPARTS%3ATP01002001",
                                "level": 4,
                                "code": "TP01002001",
                                "children": [],
                                "is_leaf": True
                            },
                            {
                                "name": "Roller bearings",
                                "url": "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-roller-bearings?CatalogPath=TRACEPARTS%3ATP01002002",
                                "level": 4,
                                "code": "TP01002002",
                                "children": [],
                                "is_leaf": True
                            }
                        ]
                    }
                ]
            },
            {
                "name": "Building & Constructions (materials and equipments)",
                "url": "https://www.traceparts.cn/en/search/traceparts-classification-building-constructions-materials-and-equipments?CatalogPath=TRACEPARTS%3ATP12",
                "level": 2,
                "code": "TP12",
                "is_leaf": False,
                "children": [
                    {
                        "name": "Buildings",
                        "url": "https://www.traceparts.cn/en/search/traceparts-classification-building-constructions-materials-and-equipments-buildings?CatalogPath=TRACEPARTS%3ATP12001",
                        "level": 3,
                        "code": "TP12001",
                        "is_leaf": False,
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
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # 提取所有叶节点
    leaves = extract_leaves(root)
    
    # 创建符合CacheLevel.CLASSIFICATION格式的缓存数据
    cache_data = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "cache_level": 1,  # CacheLevel.CLASSIFICATION
            "cache_level_name": "CLASSIFICATION",
            "version": "3.0-classification",
            "total_leaves": len(leaves),
            "total_products": 0,
            "total_specifications": 0
        },
        "root": root,
        "leaves": leaves
    }
    
    # 保存到文件
    cache_file = Path('results/cache/classification_tree_full.json')
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Pipeline V2 测试缓存文件已创建: {cache_file}")
    print(f"   • 缓存级别: CLASSIFICATION (Level 1)")
    print(f"   • 根节点: {root['name']}")
    print(f"   • 叶节点数: {len(leaves)}")
    print(f"   • 叶节点列表:")
    for i, leaf in enumerate(leaves, 1):
        print(f"     {i}. {leaf['name']} ({leaf['code']})")
        print(f"        URL: {leaf['url']}")
    
    return cache_data


if __name__ == '__main__':
    create_test_cache_v2() 