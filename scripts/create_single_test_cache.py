#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建单叶节点测试缓存
==================
仅包含1个叶节点，用于快速测试完整流程
"""

import json
from pathlib import Path
from datetime import datetime


def create_single_test_cache():
    """创建单叶节点测试缓存文件"""
    
    # 定义最小化的树结构（只包含1个叶节点）
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
                                "name": "Bearing blocks",
                                "url": "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks?CatalogPath=TRACEPARTS%3ATP01002002",
                                "level": 4,
                                "code": "TP01002002",
                                "is_leaf": False,
                                "children": [
                                    {
                                        "name": "Cartridge blocks",
                                        "url": "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-cartridge-blocks?CatalogPath=TRACEPARTS%3ATP01002002006",
                                        "level": 5,
                                        "code": "TP01002002006",
                                        "children": [],
                                        "is_leaf": True
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # 只提取1个叶节点
    leaves = [
        {
            "name": "Cartridge blocks",
            "url": "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-cartridge-blocks?CatalogPath=TRACEPARTS%3ATP01002002006",
            "level": 5,
            "code": "TP01002002006",
            "is_leaf": True
        }
    ]
    
    # 创建缓存数据
    cache_data = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "cache_level": 1,
            "cache_level_name": "CLASSIFICATION",
            "version": "3.0-classification",
            "total_leaves": len(leaves),
            "total_products": 0,
            "total_specifications": 0,
            "test_mode": True,
            "description": "Single leaf node test cache for complete pipeline testing"
        },
        "root": root,
        "leaves": leaves
    }
    
    # 保存到文件
    cache_file = Path('results/cache/classification_tree_full.json')
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 备份现有文件
    if cache_file.exists():
        backup_file = cache_file.with_suffix('.json.backup')
        cache_file.rename(backup_file)
        print(f"📋 已备份原文件到: {backup_file}")
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 单叶节点测试缓存文件已创建: {cache_file}")
    print(f"   • 测试模式: 是")
    print(f"   • 叶节点数: {len(leaves)} 个")
    print(f"   • 测试叶节点:")
    for i, leaf in enumerate(leaves, 1):
        print(f"\n   {i}. {leaf['name']} ({leaf['code']})")
        print(f"      Level: {leaf['level']}")
        print(f"      URL: {leaf['url'][:80]}...")
    
    print(f"\n💡 提示: 这是一个单叶节点测试缓存，用于完整流程测试")
    print(f"   运行 'make pipeline-v2-test' 进行完整测试")
    
    return cache_data


if __name__ == '__main__':
    create_single_test_cache() 