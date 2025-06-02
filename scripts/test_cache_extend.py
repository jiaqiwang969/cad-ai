#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试缓存管理器的产品扩展功能"""

import sys
sys.path.append('.')

from src.pipelines.cache_manager import CacheManager, CacheLevel
import json

# 创建缓存管理器（使用少量workers便于测试）
manager = CacheManager(max_workers=2)

# 获取当前缓存状态
current_level, data = manager.get_cache_level()
print(f"\n当前缓存级别: {current_level.name}")
print(f"叶节点数: {len(data.get('leaves', []))}")

# 显示叶节点产品数
for leaf in data.get('leaves', []):
    print(f"  - {leaf['code']}: products={len(leaf.get('products', []))}")

print("\n开始扩展产品链接...")

# 扩展到产品级别
new_data = manager.extend_to_products(data)

print("\n扩展后的状态:")
for leaf in new_data.get('leaves', []):
    print(f"  - {leaf['code']}: products={len(leaf.get('products', []))}")

# 保存缓存
print("\n保存缓存...")
manager.save_cache(new_data, CacheLevel.PRODUCTS)

# 重新读取验证
with open('results/cache/classification_tree_full.json', 'r') as f:
    saved_data = json.load(f)
    
print("\n保存后的验证:")
print(f"缓存级别: {saved_data['metadata']['cache_level_name']}")
for leaf in saved_data.get('leaves', []):
    print(f"  - {leaf['code']}: products={len(leaf.get('products', []))}") 