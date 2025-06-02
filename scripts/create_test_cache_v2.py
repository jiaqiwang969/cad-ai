#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建Pipeline V2测试用的缓存文件
================================
生成一个适用于渐进式缓存系统的第一级缓存文件
支持新的版本化缓存管理系统
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
    """创建Pipeline V2测试缓存文件（版本化系统）"""
    
    # 定义树结构（更丰富的测试数据）
    root = {
        "name": "TraceParts Classification",
        "url": "https://www.traceparts.cn/en/search/traceparts-classification?CatalogPath=TRACEPARTS%3ATRACEPARTS",
        "level": 1,
        "code": "TRACEPARTS_ROOT",
        "is_leaf": False,
        "children": [
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
    
    # 生成版本时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 创建符合CacheLevel.CLASSIFICATION格式的缓存数据
    cache_data = {
        "metadata": {
            "generated": datetime.now().isoformat(),
            "cache_level": 1,  # CacheLevel.CLASSIFICATION
            "cache_level_name": "CLASSIFICATION",
            "version": f"v{timestamp}",
            "total_leaves": len(leaves),
            "total_products": 0,
            "total_specifications": 0
        },
        "root": root,
        "leaves": leaves
    }
    
    # 创建缓存目录
    cache_dir = Path('results/cache')
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用版本化文件名
    cache_file = cache_dir / f'classification_tree_v{timestamp}.json'
    index_file = cache_dir / 'cache_index.json'
    
    # 保存缓存文件
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    # 创建/更新索引文件
    index_data = {
        "latest_files": {
            "classification": cache_file.name
        },
        "version_history": [
            {
                "level": "CLASSIFICATION",
                "filename": cache_file.name,
                "timestamp": datetime.now().isoformat(),
                "version": timestamp
            }
        ]
    }
    
    # 如果索引文件已存在，更新而不是覆盖
    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                existing_index = json.load(f)
            
            # 更新最新文件记录
            existing_index.setdefault('latest_files', {})
            existing_index['latest_files']['classification'] = cache_file.name
            
            # 添加到版本历史
            existing_index.setdefault('version_history', [])
            existing_index['version_history'].append(index_data['version_history'][0])
            
            # 只保留最近50个版本记录
            if len(existing_index['version_history']) > 50:
                existing_index['version_history'] = existing_index['version_history'][-50:]
            
            index_data = existing_index
        except Exception as e:
            print(f"⚠️ 读取现有索引文件失败，将创建新的: {e}")
    
    # 保存索引文件
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Pipeline V2 测试缓存文件已创建: {cache_file}")
    print(f"✅ 缓存索引文件已更新: {index_file}")
    print(f"   • 缓存级别: CLASSIFICATION (Level 1)")
    print(f"   • 版本号: v{timestamp}")
    print(f"   • 根节点: {root['name']}")
    print(f"   • 叶节点数: {len(leaves)}")
    print(f"   • 叶节点列表:")
    for i, leaf in enumerate(leaves, 1):
        print(f"     {i}. {leaf['name']} ({leaf['code']})")
        print(f"        URL: {leaf['url']}")
    
    print(f"\n使用方法:")
    print(f"   python run_cache_manager.py --status")
    print(f"   python run_cache_manager.py --level products")
    print(f"   python run_cache_manager.py --level specifications")
    
    return cache_data


if __name__ == '__main__':
    create_test_cache_v2() 