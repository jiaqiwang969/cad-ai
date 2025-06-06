#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量更新系统演示脚本
==================
展示智能差异检测和增量更新功能
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from src.pipelines.incremental_update_manager import IncrementalUpdateManager
from src.pipelines.cache_manager import CacheManager, CacheLevel


def demo_cache_status():
    """演示缓存状态查看"""
    print("="*60)
    print("📊 当前缓存状态")
    print("="*60)
    
    cache_manager = CacheManager()
    status = cache_manager.get_cache_status()
    
    print(f"当前级别: {status['current_level']}")
    print(f"缓存目录: {status['cache_directory']}")
    
    if status['latest_files']:
        print("\n最新文件:")
        for level, filename in status['latest_files'].items():
            file_size = status['file_sizes'].get(level, '未知')
            print(f"  • {level}: {filename} ({file_size})")
    
    if status['metadata']:
        metadata = status['metadata']
        print(f"\n数据统计:")
        print(f"  • 叶节点数: {metadata.get('total_leaves', 0):,}")
        print(f"  • 产品总数: {metadata.get('total_products', 0):,}")
        print(f"  • 规格总数: {metadata.get('total_specifications', 0):,}")
        print(f"  • 生成时间: {metadata.get('generated', '未知')}")


def demo_incremental_update_preview():
    """演示增量更新预览（不实际执行）"""
    print("\n" + "="*60)
    print("🔄 增量更新预览模式")
    print("="*60)
    
    update_manager = IncrementalUpdateManager()
    
    # 获取当前缓存状态
    current_level, current_data = update_manager.cache_manager.get_cache_level()
    
    if current_level == CacheLevel.NONE:
        print("⚠️ 未发现现有缓存，将执行全量构建")
        return
    
    print(f"当前缓存级别: {current_level.name}")
    
    if current_data:
        current_leaves = len(current_data.get('leaves', []))
        current_products = sum(leaf.get('product_count', 0) for leaf in current_data.get('leaves', []))
        
        print(f"当前数据量:")
        print(f"  • 叶节点: {current_leaves:,} 个")
        print(f"  • 产品: {current_products:,} 个")
        
        # 简单预测（仅作演示）
        print(f"\n预计检测内容:")
        print(f"  • 检测新增分类树结构")
        print(f"  • 对比 {current_leaves} 个叶节点的产品数量")
        print(f"  • 检测需要爬取规格的新产品")
        
        print(f"\n注意事项:")
        print(f"  • 增量更新会保留所有现有数据")
        print(f"  • 只爬取新增的叶节点、产品和规格")
        print(f"  • 运行前会自动创建数据备份")


def demo_version_history():
    """演示版本历史查看"""
    print("\n" + "="*60)
    print("📚 缓存版本历史")
    print("="*60)
    
    cache_manager = CacheManager()
    
    # 获取各级别的版本历史
    for level in [CacheLevel.CLASSIFICATION, CacheLevel.PRODUCTS, CacheLevel.SPECIFICATIONS]:
        history = cache_manager.get_version_history(level)
        
        if history:
            print(f"\n{level.name} 级别历史 (最近5个版本):")
            for i, record in enumerate(history[:5]):
                timestamp = record.get('timestamp', '未知时间')
                filename = record.get('filename', '未知文件')
                version = record.get('version', '未知版本')
                print(f"  {i+1}. {timestamp} - {version} - {filename}")
        else:
            print(f"\n{level.name} 级别: 暂无版本历史")


def main():
    """主函数"""
    print("🚀 TraceParts 增量更新系统演示")
    print("这是一个演示脚本，展示增量更新系统的功能")
    
    try:
        # 1. 显示当前缓存状态
        demo_cache_status()
        
        # 2. 演示增量更新预览
        demo_incremental_update_preview()
        
        # 3. 显示版本历史
        demo_version_history()
        
        print("\n" + "="*60)
        print("💡 使用指南")
        print("="*60)
        print("要执行实际的增量更新，请运行:")
        print("  make update                    # 完整增量更新")
        print("  make update-products           # 只更新产品链接")
        print("  make update-specifications     # 只更新产品规格")
        print("")
        print("其他有用命令:")
        print("  make cache-status              # 查看缓存状态")
        print("  make update-export             # 更新并导出结果")
        print("  make update-verbose            # 详细输出模式")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main()) 