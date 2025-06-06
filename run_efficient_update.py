#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraceParts 高效增量更新系统入口
============================
智能快速检测，大幅提升更新效率
"""

import argparse
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from src.pipelines.efficient_incremental_manager import EfficientIncrementalManager, DetectionConfig
from src.pipelines.cache_manager import CacheLevel


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TraceParts 高效增量更新系统')
    
    # 更新级别
    parser.add_argument(
        '--level',
        type=str,
        choices=['classification', 'products', 'specifications'],
        default='specifications',
        help='目标更新级别 (默认: specifications)'
    )
    
    # 性能配置
    parser.add_argument('--workers', type=int, default=8, help='最大并发数 (默认: 8)')
    parser.add_argument('--sample-ratio', type=float, default=0.1, help='分类树采样比例 (默认: 0.1)')
    parser.add_argument('--product-samples', type=int, default=50, help='产品检测采样数 (默认: 50)')
    parser.add_argument('--spec-samples', type=int, default=20, help='规格检测采样数 (默认: 20)')
    
    # 时间配置
    parser.add_argument('--min-interval', type=int, default=2, help='最小检测间隔小时数 (默认: 2)')
    parser.add_argument('--quick-timeout', type=int, default=30, help='快速检测超时秒数 (默认: 30)')
    
    # 阈值配置
    parser.add_argument('--change-threshold', type=float, default=0.05, help='变化阈值 (默认: 0.05)')
    parser.add_argument('--force-full-ratio', type=float, default=0.2, help='强制全量检查比例 (默认: 0.2)')
    
    # 其他参数
    parser.add_argument('--cache-dir', type=str, default='results/cache', help='缓存目录')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径（可选）')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    # 映射缓存级别
    level_map = {
        'classification': CacheLevel.CLASSIFICATION,
        'products': CacheLevel.PRODUCTS,
        'specifications': CacheLevel.SPECIFICATIONS
    }
    target_level = level_map[args.level]
    
    # 创建检测配置
    config = DetectionConfig(
        classification_sample_ratio=args.sample_ratio,
        products_sample_size=args.product_samples,
        specs_sample_size=args.spec_samples,
        min_check_interval_hours=args.min_interval,
        max_parallel_workers=args.workers,
        quick_detection_timeout=args.quick_timeout,
        change_threshold=args.change_threshold,
        force_full_check_ratio=args.force_full_ratio
    )
    
    # 创建并运行高效增量更新管理器
    update_manager = EfficientIncrementalManager(
        cache_dir=args.cache_dir,
        config=config
    )
    
    try:
        print("⚡ TraceParts 高效增量更新系统")
        print(f"配置参数: 采样比例={args.sample_ratio}, 产品采样={args.product_samples}, 并发数={args.workers}")
        print("")
        
        # 运行高效增量更新
        updated_data = update_manager.run_efficient_update(target_level=target_level)
        
        # 如果指定了输出文件，保存结果
        if args.output:
            import json
            from datetime import datetime
            
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 添加导出元数据
            export_data = updated_data.copy()
            export_data['export_metadata'] = {
                'exported_at': datetime.now().isoformat(),
                'export_file': str(output_path),
                'update_type': 'efficient_incremental',
                'pipeline_version': '4.0-efficient',
                'detection_config': {
                    'sample_ratio': args.sample_ratio,
                    'product_samples': args.product_samples,
                    'spec_samples': args.spec_samples,
                    'workers': args.workers
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            file_size_mb = output_path.stat().st_size / 1024 / 1024
            print(f"\n📄 结果已导出到: {output_path}")
            print(f"   文件大小: {file_size_mb:.1f} MB")
        
        print("\n⚡ 高效增量更新完成！")
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
        return 1
    except Exception as e:
        print(f"\n❌ 高效增量更新失败: {e}")
        return 1


if __name__ == '__main__':
    exit(main()) 