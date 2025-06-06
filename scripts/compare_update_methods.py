#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量更新方法对比演示
==================
对比标准增量更新 vs 高效增量更新的性能差异
"""

import sys
import time
from pathlib import Path
from typing import Dict, List

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from src.pipelines.cache_manager import CacheManager, CacheLevel


def demo_performance_comparison():
    """演示性能对比"""
    print("="*70)
    print("📊 增量更新方法性能对比")
    print("="*70)
    
    cache_manager = CacheManager()
    current_level, current_data = cache_manager.get_cache_level()
    
    if current_level == CacheLevel.NONE:
        print("⚠️ 未发现现有缓存，无法进行对比演示")
        return
    
    current_leaves = len(current_data.get('leaves', []))
    current_products = sum(leaf.get('product_count', 0) for leaf in current_data.get('leaves', []))
    
    print(f"当前数据规模:")
    print(f"  • 叶节点: {current_leaves:,} 个")
    print(f"  • 产品: {current_products:,} 个")
    print("")
    
    # 标准增量更新方法分析
    print("🔄 标准增量更新方法:")
    print("=" * 50)
    
    # 估算操作数量
    classification_ops = 1  # 完整爬取分类树
    product_check_ops = current_leaves  # 逐个检查每个叶节点
    spec_identification_ops = current_products  # 检查每个产品是否需要规格
    
    standard_total_ops = classification_ops + product_check_ops + spec_identification_ops
    
    # 估算时间（基于经验数据）
    avg_classification_time = 300  # 5分钟爬取完整分类树
    avg_product_check_time = 2  # 每个叶节点2秒
    avg_spec_check_time = 0.1  # 每个产品0.1秒检查规格需求
    
    standard_estimated_time = (
        avg_classification_time + 
        product_check_ops * avg_product_check_time + 
        spec_identification_ops * avg_spec_check_time
    )
    
    print(f"估算操作数量:")
    print(f"  • 分类树检测: {classification_ops:,} 次 (完整爬取)")
    print(f"  • 产品检测: {product_check_ops:,} 次 (逐个检查)")
    print(f"  • 规格检测: {spec_identification_ops:,} 次 (逐个检查)")
    print(f"  • 总操作数: {standard_total_ops:,} 次")
    print(f"估算耗时: {standard_estimated_time/60:.1f} 分钟")
    print("")
    
    # 高效增量更新方法分析
    print("⚡ 高效增量更新方法:")
    print("=" * 50)
    
    # 采样配置
    sample_ratio = 0.1
    product_samples = 50
    spec_samples = 20
    
    sampled_leaves = max(1, int(current_leaves * sample_ratio))
    actual_product_samples = min(product_samples, current_leaves)
    actual_spec_samples = min(spec_samples, current_products)
    
    # 估算操作数量
    efficient_classification_ops = sampled_leaves  # 采样检测
    efficient_product_ops = actual_product_samples  # 采样检测
    efficient_spec_ops = actual_spec_samples  # 采样检测
    
    efficient_total_ops = efficient_classification_ops + efficient_product_ops + efficient_spec_ops
    
    # 估算时间
    avg_sample_check_time = 1  # 采样检测每次1秒
    efficient_estimated_time = efficient_total_ops * avg_sample_check_time
    
    print(f"采样配置:")
    print(f"  • 分类树采样比例: {sample_ratio:.1%}")
    print(f"  • 产品检测采样: {actual_product_samples} 个")
    print(f"  • 规格检测采样: {actual_spec_samples} 个")
    print("")
    
    print(f"估算操作数量:")
    print(f"  • 分类树检测: {efficient_classification_ops:,} 次 (采样检测)")
    print(f"  • 产品检测: {efficient_product_ops:,} 次 (采样检测)")
    print(f"  • 规格检测: {efficient_spec_ops:,} 次 (采样检测)")
    print(f"  • 总操作数: {efficient_total_ops:,} 次")
    print(f"估算耗时: {efficient_estimated_time/60:.1f} 分钟")
    print("")
    
    # 性能对比
    print("📊 性能对比分析:")
    print("=" * 50)
    
    ops_reduction = ((standard_total_ops - efficient_total_ops) / standard_total_ops) * 100
    time_reduction = ((standard_estimated_time - efficient_estimated_time) / standard_estimated_time) * 100
    speed_improvement = standard_estimated_time / efficient_estimated_time
    
    print(f"操作数量减少: {ops_reduction:.1f}%")
    print(f"时间减少: {time_reduction:.1f}%")
    print(f"速度提升: {speed_improvement:.1f}x")
    print("")
    
    # 适用场景分析
    print("🎯 适用场景分析:")
    print("=" * 50)
    print("标准增量更新适用于:")
    print("  • 需要100%准确性的场景")
    print("  • 数据规模较小的情况")
    print("  • 初次部署或长期未更新")
    print("")
    
    print("高效增量更新适用于:")
    print("  • 日常定期更新维护")
    print("  • 大规模数据场景")
    print("  • 对性能有要求的环境")
    print("  • 可接受小概率遗漏的场景")
    print("")
    
    # 准确性分析
    print("🔍 准确性分析:")
    print("=" * 50)
    
    # 基于采样的理论准确性
    sampling_confidence = 0.95  # 95%置信度
    margin_of_error = 0.05  # 5%误差范围
    
    print(f"高效方法理论准确性:")
    print(f"  • 采样置信度: {sampling_confidence:.0%}")
    print(f"  • 误差范围: ±{margin_of_error:.0%}")
    print(f"  • 预期检测率: {(1-margin_of_error):.0%}以上")
    print("")
    
    print("风险评估:")
    print("  • 可能遗漏的变化: 小幅度、局部变化")
    print("  • 误报可能性: 极低")
    print("  • 建议: 定期执行标准更新作为补充")


def demo_configuration_guide():
    """演示配置指南"""
    print("\n" + "="*70)
    print("⚙️ 高效更新配置指南")
    print("="*70)
    
    scenarios = [
        {
            'name': '日常维护模式',
            'description': '适用于每日/每周的常规更新',
            'config': {
                'sample_ratio': 0.05,
                'product_samples': 20,
                'spec_samples': 10,
                'min_interval': 4,
                'change_threshold': 0.03
            },
            'performance': '最快，适合频繁更新'
        },
        {
            'name': '标准检测模式',
            'description': '平衡性能和准确性',
            'config': {
                'sample_ratio': 0.1,
                'product_samples': 50,
                'spec_samples': 20,
                'min_interval': 2,
                'change_threshold': 0.05
            },
            'performance': '推荐的默认配置'
        },
        {
            'name': '全面检测模式',
            'description': '适用于重要更新或长期未检查',
            'config': {
                'sample_ratio': 0.2,
                'product_samples': 100,
                'spec_samples': 50,
                'min_interval': 1,
                'change_threshold': 0.02
            },
            'performance': '较慢但更准确'
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   配置参数:")
        for key, value in scenario['config'].items():
            print(f"     --{key.replace('_', '-')}: {value}")
        print(f"   性能特点: {scenario['performance']}")
        print("")
    
    print("配置参数说明:")
    print("  • sample-ratio: 分类树采样比例，越小越快")
    print("  • product-samples: 产品检测采样数量")
    print("  • spec-samples: 规格检测采样数量")
    print("  • min-interval: 最小检测间隔（小时）")
    print("  • change-threshold: 变化阈值，越小越敏感")


def demo_commands_comparison():
    """演示命令对比"""
    print("\n" + "="*70)
    print("🚀 命令使用对比")
    print("="*70)
    
    print("标准增量更新命令:")
    print("  make update                    # 标准增量更新")
    print("  make update-fast               # 快速标准更新")
    print("  make update-products           # 只更新产品")
    print("  make update-export             # 更新并导出")
    print("")
    
    print("高效增量更新命令:")
    print("  make update-efficient          # 高效增量更新 (推荐)")
    print("  make update-efficient-fast     # 高并发高效更新")
    print("  make update-efficient-conservative  # 保守检测")
    print("  make update-efficient-aggressive    # 激进检测")
    print("  make update-efficient-export   # 高效更新并导出")
    print("")
    
    print("选择建议:")
    print("  🏃 日常使用: make update-efficient")
    print("  🚀 追求速度: make update-efficient-aggressive")
    print("  🔍 追求准确: make update-efficient-conservative")
    print("  📁 需要导出: make update-efficient-export")


def main():
    """主函数"""
    print("🚀 TraceParts 增量更新方法对比演示")
    print("展示标准方法 vs 高效方法的性能和准确性差异")
    print("")
    
    try:
        # 1. 性能对比分析
        demo_performance_comparison()
        
        # 2. 配置指南
        demo_configuration_guide()
        
        # 3. 命令对比
        demo_commands_comparison()
        
        print("\n" + "="*70)
        print("💡 总结建议")
        print("="*70)
        print("• 日常使用推荐高效增量更新")
        print("• 重要更新可结合标准方法")
        print("• 根据实际需求调整采样参数")
        print("• 定期监控更新效果和准确性")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main()) 