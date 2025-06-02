#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版完整流水线 V2 - 基于渐进式缓存管理器
=======================================
使用统一的缓存管理器，支持三阶段缓存
"""

import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.pipelines.cache_manager import CacheManager, CacheLevel
from src.utils.thread_safe_logger import ThreadSafeLogger


class OptimizedFullPipelineV2:
    """基于缓存管理器的优化流水线"""
    
    def __init__(self, max_workers: int = 32, cache_dir: str = 'results/cache'):
        self.max_workers = max_workers
        self.cache_dir = cache_dir
        self.logger = ThreadSafeLogger("pipeline-v2", logging.INFO)
        
        # 使用缓存管理器
        self.cache_manager = CacheManager(cache_dir=cache_dir, max_workers=max_workers)
        
        # 统计信息
        self.stats = {
            'start_time': None,
            'end_time': None,
            'duration': None,
            'cache_level_start': None,
            'cache_level_end': None,
            'total_leaves': 0,
            'total_products': 0,
            'total_specifications': 0
        }
    
    def run(self, output_file: str = None, cache_enabled: bool = True, target_level: CacheLevel = CacheLevel.SPECIFICATIONS):
        """
        运行优化版流水线V2
        
        Args:
            output_file: 输出文件路径
            cache_enabled: 是否启用缓存
            target_level: 目标缓存级别
        """
        self.stats['start_time'] = datetime.now()
        
        self.logger.info("\n" + "="*60)
        self.logger.info("🚀 TraceParts 产品数据爬取系统 v4.0")
        self.logger.info("   基于渐进式缓存管理器")
        self.logger.info("="*60)
        
        # 显示当前缓存状态
        current_level, _ = self.cache_manager.get_cache_level()
        self.stats['cache_level_start'] = current_level.name
        
        self.logger.info(f"📊 缓存状态:")
        self.logger.info(f"   • 当前级别: {current_level.name}")
        self.logger.info(f"   • 目标级别: {target_level.name}")
        self.logger.info(f"   • 缓存目录: {self.cache_dir}")
        self.logger.info(f"   • 并发线程: {self.max_workers}")
        
        if not cache_enabled:
            self.logger.info("   • ⚠️  缓存已禁用，将强制刷新")
        
        self.logger.info("="*60)
        
        try:
            # 使用缓存管理器运行
            data = self.cache_manager.run_progressive_cache(
                target_level=target_level,
                force_refresh=not cache_enabled
            )
            
            if not data:
                self.logger.error("❌ 数据获取失败")
                return None
            
            # 更新统计
            self._update_stats(data)
            
            # 保存结果（如果指定了输出文件）
            if output_file:
                self._save_results(data, output_file)
            
            # 打印汇总
            self._print_summary()
            
            return data
            
        except Exception as e:
            self.logger.error(f"流水线执行失败: {e}", exc_info=True)
            raise
    
    def _update_stats(self, data: Dict):
        """更新统计信息"""
        metadata = data.get('metadata', {})
        self.stats['cache_level_end'] = metadata.get('cache_level_name', 'UNKNOWN')
        self.stats['total_leaves'] = metadata.get('total_leaves', 0)
        self.stats['total_products'] = metadata.get('total_products', 0)
        self.stats['total_specifications'] = metadata.get('total_specifications', 0)
    
    def _save_results(self, data: Dict, output_file: str):
        """保存结果到指定文件"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 添加导出元数据
        export_data = data.copy()
        export_data['export_metadata'] = {
            'exported_at': datetime.now().isoformat(),
            'export_file': str(output_path),
            'pipeline_version': '4.0-cache-manager'
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        file_size_mb = output_path.stat().st_size / 1024 / 1024
        self.logger.info(f"\n📄 结果已导出到: {output_path}")
        self.logger.info(f"   文件大小: {file_size_mb:.1f} MB")
    
    def _print_summary(self):
        """打印汇总信息"""
        self.stats['end_time'] = datetime.now()
        self.stats['duration'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        duration_min = self.stats['duration'] / 60
        
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 爬取完成 - 最终统计")
        self.logger.info("="*60)
        
        # 时间统计
        self.logger.info(f"⏱️  总耗时: {duration_min:.1f} 分钟")
        
        # 缓存级别变化
        self.logger.info(f"\n📈 缓存进度:")
        self.logger.info(f"   • 起始级别: {self.stats['cache_level_start']}")
        self.logger.info(f"   • 最终级别: {self.stats['cache_level_end']}")
        
        # 数据统计
        self.logger.info(f"\n📊 数据统计:")
        self.logger.info(f"   • 叶节点数: {self.stats['total_leaves']:,}")
        self.logger.info(f"   • 产品总数: {self.stats['total_products']:,}")
        self.logger.info(f"   • 规格总数: {self.stats['total_specifications']:,}")
        
        # 平均统计
        if self.stats['total_leaves'] > 0:
            avg_products = self.stats['total_products'] / self.stats['total_leaves']
            self.logger.info(f"\n📈 平均统计:")
            self.logger.info(f"   • 每个叶节点平均产品数: {avg_products:.1f}")
            
        if self.stats['total_products'] > 0:
            avg_specs = self.stats['total_specifications'] / self.stats['total_products']
            self.logger.info(f"   • 每个产品平均规格数: {avg_specs:.1f}")
        
        self.logger.info("="*60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TraceParts 优化版流水线 V2 (基于缓存管理器)')
    
    # 缓存级别
    parser.add_argument(
        '--level',
        type=str,
        choices=['classification', 'products', 'specifications'],
        default='specifications',
        help='目标缓存级别 (默认: specifications)'
    )
    
    # 其他参数
    parser.add_argument('--workers', type=int, default=32, help='最大并发数 (默认: 32)')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径')
    parser.add_argument('--no-cache', action='store_true', help='禁用缓存，强制重新爬取')
    parser.add_argument('--cache-dir', type=str, default='results/cache', help='缓存目录')
    
    args = parser.parse_args()
    
    # 映射缓存级别
    level_map = {
        'classification': CacheLevel.CLASSIFICATION,
        'products': CacheLevel.PRODUCTS,
        'specifications': CacheLevel.SPECIFICATIONS
    }
    target_level = level_map[args.level]
    
    # 创建并运行流水线
    pipeline = OptimizedFullPipelineV2(
        max_workers=args.workers,
        cache_dir=args.cache_dir
    )
    
    pipeline.run(
        output_file=args.output,
        cache_enabled=not args.no_cache,
        target_level=target_level
    )


if __name__ == '__main__':
    main() 