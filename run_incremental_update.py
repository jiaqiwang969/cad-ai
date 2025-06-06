#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TraceParts 增量更新系统入口
========================
智能差异检测，只更新新增内容
"""

import argparse
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent))

from src.pipelines.incremental_update_manager import IncrementalUpdateManager
from src.pipelines.cache_manager import CacheLevel


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TraceParts 智能增量更新系统')
    
    # 更新级别
    parser.add_argument(
        '--level',
        type=str,
        choices=['classification', 'products', 'specifications'],
        default='specifications',
        help='目标更新级别 (默认: specifications)'
    )
    
    # 其他参数
    parser.add_argument('--workers', type=int, default=16, help='最大并发数 (默认: 16)')
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
    
    # 创建并运行增量更新管理器
    update_manager = IncrementalUpdateManager(
        cache_dir=args.cache_dir,
        max_workers=args.workers
    )
    
    try:
        # 运行增量更新
        updated_data = update_manager.run_incremental_update(target_level=target_level)
        
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
                'update_type': 'incremental',
                'pipeline_version': '4.0-incremental'
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            file_size_mb = output_path.stat().st_size / 1024 / 1024
            print(f"\n📄 结果已导出到: {output_path}")
            print(f"   文件大小: {file_size_mb:.1f} MB")
        
        print("\n🎉 增量更新完成！")
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
        return 1
    except Exception as e:
        print(f"\n❌ 增量更新失败: {e}")
        return 1


if __name__ == '__main__':
    exit(main()) 