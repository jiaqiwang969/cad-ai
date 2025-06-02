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
import logging
import json
from pathlib import Path


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
    
    # 新增：状态和历史查看功能
    parser.add_argument('--status', action='store_true', help='显示缓存状态信息')
    parser.add_argument('--history', action='store_true', help='显示版本历史记录')
    parser.add_argument('--cleanup', action='store_true', help='清理旧版本文件')
    parser.add_argument('--errors', action='store_true', help='显示最新的错误日志')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # 减少其他模块的日志噪音
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    try:
        # 创建缓存管理器
        cache_manager = CacheManager(
            cache_dir=args.cache_dir,
            max_workers=args.workers
        )
        
        # 处理状态查看请求
        if args.status:
            print("\n" + "="*60)
            print("📊 缓存状态信息")
            print("="*60)
            
            status = cache_manager.get_cache_status()
            print(f"📁 缓存目录: {status['cache_directory']}")
            print(f"📈 当前级别: {status['current_level']}")
            
            if status['latest_files']:
                print("\n📄 最新缓存文件:")
                for level, filename in status['latest_files'].items():
                    size = status['file_sizes'].get(level, 'N/A')
                    print(f"   • {level.upper()}: {filename} ({size})")
            
            if status['metadata']:
                metadata = status['metadata']
                print(f"\n🏷️ 元数据信息:")
                print(f"   • 版本: {metadata.get('version', 'N/A')}")
                print(f"   • 生成时间: {metadata.get('generated', 'N/A')}")
                print(f"   • 叶节点数: {metadata.get('total_leaves', 0)}")
                print(f"   • 产品总数: {metadata.get('total_products', 0)}")
                print(f"   • 规格总数: {metadata.get('total_specifications', 0)}")
            
            print("="*60)
            return
        
        # 处理历史查看请求
        if args.history:
            print("\n" + "="*60)
            print("📋 版本历史记录")
            print("="*60)
            
            history = cache_manager.get_version_history()
            if not history:
                print("暂无版本历史记录")
                return
            
            for record in history[:10]:  # 只显示最近10个版本
                level = record.get('level', 'UNKNOWN')
                version = record.get('version', 'N/A')
                timestamp = record.get('timestamp', 'N/A')
                filename = record.get('filename', 'N/A')
                
                if timestamp != 'N/A':
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                print(f"🔸 [{level}] {version} - {timestamp}")
                print(f"   文件: {filename}")
                print()
            
            print("="*60)
            return
        
        # 处理清理请求
        if args.cleanup:
            print("\n🧹 开始清理旧版本文件...")
            
            for level in [CacheLevel.CLASSIFICATION, CacheLevel.PRODUCTS, CacheLevel.SPECIFICATIONS]:
                cache_manager._cleanup_old_versions(level, keep_versions=3)
            
            print("✅ 清理完成！")
            return
        
        # 处理错误日志查看请求
        if args.errors:
            print("\n" + "="*60)
            print("🚨 错误日志查看")
            print("="*60)
            
            error_logs_dir = Path(args.cache_dir) / 'error_logs'
            if not error_logs_dir.exists():
                print("暂无错误日志目录")
                return
            
            # 查找最新的错误日志文件
            error_files = list(error_logs_dir.glob('error_log_v*.json'))
            if not error_files:
                print("暂无错误日志文件")
                return
            
            # 选择最新的错误日志
            latest_error_file = max(error_files, key=lambda x: x.stat().st_mtime)
            
            try:
                with open(latest_error_file, 'r', encoding='utf-8') as f:
                    error_data = json.load(f)
                
                print(f"📄 错误日志文件: {latest_error_file.name}")
                print(f"🕐 生成时间: {error_data.get('generated', 'N/A')}")
                print(f"📌 版本: {error_data.get('version', 'N/A')}")
                
                summary = error_data.get('summary', {})
                print(f"\n📊 错误统计:")
                print(f"   • 产品链接失败: {summary.get('total_product_errors', 0)} 个")
                print(f"   • 规格爬取失败: {summary.get('total_specification_errors', 0)} 个")
                print(f"   • 零规格产品: {summary.get('zero_specs_count', 0)} 个")
                print(f"   • 异常数量: {summary.get('exception_count', 0)} 个")
                
                # 显示详细的错误信息
                details = error_data.get('details', {})
                
                if details.get('products'):
                    print(f"\n🔴 产品链接错误:")
                    for i, error in enumerate(details['products'][:5], 1):  # 只显示前5个
                        print(f"   {i}. [{error.get('error_type', 'unknown')}] {error.get('leaf_code', 'N/A')}")
                        print(f"      URL: {error.get('leaf_url', 'N/A')}")
                        if 'exception' in error:
                            print(f"      错误: {error['exception']}")
                        print()
                    
                    if len(details['products']) > 5:
                        print(f"   ... 还有 {len(details['products']) - 5} 个错误记录")
                
                if details.get('specifications'):
                    print(f"\n🔴 产品规格错误:")
                    for i, error in enumerate(details['specifications'][:5], 1):  # 只显示前5个
                        print(f"   {i}. [{error.get('error_type', 'unknown')}] 规格数: {error.get('spec_count', 0)}")
                        print(f"      URL: {error.get('product_url', 'N/A')}")
                        if 'exception' in error:
                            print(f"      错误: {error['exception']}")
                        print()
                    
                    if len(details['specifications']) > 5:
                        print(f"   ... 还有 {len(details['specifications']) - 5} 个错误记录")
                
            except Exception as e:
                print(f"读取错误日志失败: {e}")
            
            print("="*60)
            return
        
        # 获取目标级别
        target_level_map = {
            'classification': CacheLevel.CLASSIFICATION,
            'products': CacheLevel.PRODUCTS,
            'specifications': CacheLevel.SPECIFICATIONS
        }
        target_level = target_level_map[args.level]
        
        # 运行渐进式缓存
        cache_manager.run_progressive_cache(
            target_level=target_level,
            force_refresh=args.force
        )
    except Exception as e:
        print(f"执行过程中发生错误: {e}")


if __name__ == '__main__':
    main() 