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
            'total_specifications': 0,
            'is_test_run': False # Added for test runs
        }
    
    def run(self, output_file: str = None, cache_enabled: bool = True, target_level: CacheLevel = CacheLevel.SPECIFICATIONS, retry_failed_only: bool = False, test_url: Optional[str] = None): # Added test_url
        """
        运行优化版流水线V2
        
        Args:
            output_file: 输出文件路径
            cache_enabled: 是否启用缓存
            target_level: 目标缓存级别
            retry_failed_only: 是否仅重跑失败的产品规格
            test_url: 如果提供，则只测试此单个URL
        """
        self.stats['start_time'] = datetime.now()
        self.stats['is_test_run'] = bool(test_url)

        self.logger.info("\n" + "="*60)
        if test_url:
            self.logger.info("🚀 TraceParts 产品数据爬取系统 v4.0 - SINGLE URL TEST MODE")
            self.logger.info(f"   🧪 测试URL: {test_url}")
        else:
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
            data = None
            if test_url:
                self.logger.info(f"▶️ 开始处理单个测试URL: {test_url}")
                # We will call a new method in CacheManager for single URL testing
                data = self.cache_manager.run_single_url_test(
                    test_url=test_url,
                    target_level=target_level,
                    force_refresh=not cache_enabled,
                    # retry_failed_only might not be directly applicable or needs careful thought for single URL
                )
                if data: # If data is returned, it implies success for the single URL stages
                    self.logger.info(f"✅ 单个URL测试处理完成: {test_url}")
                    # For single URL, adapt stats update if necessary based on what run_single_url_test returns
                    # For now, let's assume it returns a structure that _update_stats can somewhat handle
                    # or we might need a specialized stats update for test mode.
                    if 'metadata' in data: # if the single test returns a compatible structure
                         self._update_stats(data)
                    else: # Minimal stats for single URL test if structure is different
                        self.stats['total_leaves'] = 1 if data.get('is_leaf_node', False) else 0
                        self.stats['total_products'] = data.get('product_count', 0)
                        self.stats['total_specifications'] = data.get('specification_count', 0)
                        self.stats['cache_level_end'] = target_level.name # Assume target level reached for test
            else:
                # 使用缓存管理器运行
                data = self.cache_manager.run_progressive_cache(
                    target_level=target_level,
                    force_refresh=not cache_enabled,
                    retry_failed_only=retry_failed_only
                )
                if data:
                    self._update_stats(data)
            
            if not data:
                self.logger.error("❌ 数据获取失败")
                return None
            
            # 保存结果（如果指定了输出文件）
            if output_file and not test_url: # Typically don't save full output for a single test URL unless specified
                self._save_results(data, output_file)
            elif output_file and test_url:
                 self.logger.info(f"📝 测试URL结果将不会自动保存到主输出文件 {output_file}. 查看控制台日志.")
            
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
        """保存结果到指定文件 - 直接调用cache_manager的test-09-1格式生成方法"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 🎯 直接调用我们已经修改好的generate_test_09_1_format_outputs方法
        self.logger.info(f"📋 使用CacheManager生成test-09-1标准格式...")
        
        try:
            # 调用cache_manager的方法生成标准格式JSON
            json_results = self.cache_manager.generate_test_09_1_format_outputs(
                data,
                save_to_file=False,  # 我们自己保存文件
                output_dir=None
            )
            
            if not json_results:
                self.logger.error("❌ CacheManager生成test-09-1格式失败")
                return
            
            # 🎯 保存JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_results, f, indent=2, ensure_ascii=False)
            
            # 🎯 输出摘要
            self.logger.info(f"💾 简化结果已保存到: {output_path.absolute()}")
            
            # 使用JSON结果中的数据输出摘要
            self._print_test_09_1_summary_from_json(json_results)
            
            self.logger.info(f"💾 文件路径: {output_path.absolute()}")
            
        except Exception as e:
            self.logger.error(f"❌ 调用CacheManager生成test-09-1格式时出错: {e}", exc_info=True)
            # 如果出错，回退到简单格式
            simple_fallback = {
                'extraction_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'error': f'Failed to generate test-09-1 format: {str(e)}',
                'fallback_data': data.get('metadata', {})
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(simple_fallback, f, indent=2, ensure_ascii=False)
            self.logger.info(f"💾 错误回退数据已保存到: {output_path.absolute()}")
    
    def _print_test_09_1_summary_from_json(self, json_results: Dict):
        """从JSON结果输出摘要（严格按照test-09-1格式）"""
        if not json_results or not json_results.get('specifications'):
            self.logger.info("📋 无规格数据可显示")
            return
        
        specifications = json_results['specifications']
        base_product = json_results.get('base_product', {})
        table_headers = json_results.get('table_headers', [])
        
        # 模拟test-09-1的详细输出
        self.logger.info("\n" + "="*80)
        self.logger.info("📋 提取结果摘要")
        self.logger.info("="*80)
        self.logger.info(f"基础产品: {base_product.get('name', 'unknown')}")
        self.logger.info(f"产品ID: {base_product.get('id', 'unknown')}")
        self.logger.info(f"表格表头: {table_headers}")
        self.logger.info(f"找到规格数量: {len(specifications)}")
        self.logger.info("\n🔗 规格列表:")
        
        # 显示前5个规格
        for i, spec_data in enumerate(specifications[:5], 1):
            self.logger.info(f"{i:2d}. {spec_data.get('reference', 'unknown')}")
            parameters = spec_data.get('parameters', {})
            for param_name, param_value in parameters.items():
                self.logger.info(f"     {param_name}: {param_value}")
        
        if len(specifications) > 5:
            remaining = len(specifications) - 5
            self.logger.info(f"... 还有 {remaining} 个规格")
        
        self.logger.info("="*80)

    
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
    parser.add_argument('--retry-failed-only', action='store_true', help='仅重跑失败的产品规格')
    parser.add_argument('--test-url', type=str, default=None, help='A single URL to test the pipeline with.') # Added
    
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
        target_level=target_level,
        retry_failed_only=args.retry_failed_only,
        test_url=args.test_url # Pass test_url
    )


if __name__ == '__main__':
    main() 