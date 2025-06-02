#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraceParts 渐进式缓存管理器
==========================
支持三阶段缓存构建：
1. 分类树
2. 产品链接
3. 产品规格
"""

import argparse
from src.pipelines.cache_manager import CacheManager, CacheLevel


def main():
    parser = argparse.ArgumentParser(description='TraceParts 渐进式缓存管理')
    
    # 缓存级别选择
    parser.add_argument(
        '--level', 
        type=str, 
        choices=['classification', 'products', 'specifications'],
        default='specifications',
        help='目标缓存级别 (默认: specifications)'
    )
    
    # 其他参数
    parser.add_argument('--workers', type=int, default=16, help='最大并发数 (默认: 16)')
    parser.add_argument('--force', action='store_true', help='强制刷新所有缓存')
    parser.add_argument('--cache-dir', type=str, default='results/cache', help='缓存目录')
    
    args = parser.parse_args()
    
    # 映射级别
    level_map = {
        'classification': CacheLevel.CLASSIFICATION,
        'products': CacheLevel.PRODUCTS,
        'specifications': CacheLevel.SPECIFICATIONS
    }
    target_level = level_map[args.level]
    
    # 创建缓存管理器
    manager = CacheManager(cache_dir=args.cache_dir, max_workers=args.workers)
    
    # 运行渐进式缓存
    manager.run_progressive_cache(
        target_level=target_level,
        force_refresh=args.force
    )


if __name__ == '__main__':
    main() 