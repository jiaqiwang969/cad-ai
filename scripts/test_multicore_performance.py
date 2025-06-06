#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多核性能对比测试
===============
比较原版和多核优化版的性能差异
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.crawler.specifications import SpecificationsCrawler
from src.crawler.specifications_multicore import MultiCoreSpecificationsCrawler


def test_original_version(product_urls):
    """测试原版爬虫"""
    print("\n" + "="*60)
    print("🧪 测试原版爬虫")
    print("="*60)
    
    crawler = SpecificationsCrawler()
    start_time = time.time()
    
    # 使用批量接口
    results = crawler.extract_batch_specifications(product_urls, max_workers=4)
    
    elapsed = time.time() - start_time
    success_count = sum(1 for r in results if r['success'])
    total_specs = sum(r['count'] for r in results)
    
    print(f"\n📊 原版爬虫结果:")
    print(f"   • 处理产品数: {len(product_urls)}")
    print(f"   • 成功: {success_count}")
    print(f"   • 总规格数: {total_specs}")
    print(f"   • 总耗时: {elapsed:.1f} 秒")
    print(f"   • 平均速度: {len(product_urls)/elapsed:.2f} 个/秒")
    print(f"   • 平均每个产品: {elapsed/len(product_urls):.1f} 秒")
    
    return {
        'version': 'original',
        'total_products': len(product_urls),
        'success_count': success_count,
        'total_specs': total_specs,
        'elapsed_time': elapsed,
        'avg_speed': len(product_urls)/elapsed,
        'avg_per_product': elapsed/len(product_urls)
    }


def test_multicore_version(product_urls, max_workers=None):
    """测试多核优化版爬虫"""
    import os
    workers = max_workers or min(16, (os.cpu_count() or 1) * 2)
    
    print("\n" + "="*60)
    print(f"🚀 测试多核优化版爬虫 (工作线程: {workers})")
    print("="*60)
    
    crawler = MultiCoreSpecificationsCrawler(max_workers=workers)
    start_time = time.time()
    
    # 使用批量接口
    results = crawler.extract_batch_specifications(product_urls)
    
    elapsed = time.time() - start_time
    success_count = sum(1 for r in results if r['success'])
    total_specs = sum(r['count'] for r in results)
    
    print(f"\n📊 多核优化版结果:")
    print(f"   • 处理产品数: {len(product_urls)}")
    print(f"   • 成功: {success_count}")
    print(f"   • 总规格数: {total_specs}")
    print(f"   • 总耗时: {elapsed:.1f} 秒")
    print(f"   • 平均速度: {len(product_urls)/elapsed:.2f} 个/秒")
    print(f"   • 平均每个产品: {elapsed/len(product_urls):.1f} 秒")
    
    return {
        'version': 'multicore',
        'workers': workers,
        'total_products': len(product_urls),
        'success_count': success_count,
        'total_specs': total_specs,
        'elapsed_time': elapsed,
        'avg_speed': len(product_urls)/elapsed,
        'avg_per_product': elapsed/len(product_urls)
    }


def compare_results(original_result, multicore_result):
    """比较两个版本的结果"""
    print("\n" + "="*60)
    print("📊 性能对比分析")
    print("="*60)
    
    # 速度提升
    speedup = multicore_result['avg_speed'] / original_result['avg_speed']
    time_reduction = (original_result['elapsed_time'] - multicore_result['elapsed_time']) / original_result['elapsed_time'] * 100
    
    print(f"\n🚀 性能提升:")
    print(f"   • 速度提升: {speedup:.2f}x")
    print(f"   • 时间减少: {time_reduction:.1f}%")
    print(f"   • 原版耗时: {original_result['elapsed_time']:.1f} 秒")
    print(f"   • 多核版耗时: {multicore_result['elapsed_time']:.1f} 秒")
    print(f"   • 节省时间: {original_result['elapsed_time'] - multicore_result['elapsed_time']:.1f} 秒")
    
    # 成功率对比
    original_success_rate = original_result['success_count'] / original_result['total_products'] * 100
    multicore_success_rate = multicore_result['success_count'] / multicore_result['total_products'] * 100
    
    print(f"\n✅ 成功率对比:")
    print(f"   • 原版成功率: {original_success_rate:.1f}%")
    print(f"   • 多核版成功率: {multicore_success_rate:.1f}%")
    
    # 估算77万产品的时间
    print(f"\n⏱️  77万产品预估时间:")
    original_hours = (770000 * original_result['avg_per_product']) / 3600
    multicore_hours = (770000 * multicore_result['avg_per_product']) / 3600
    
    print(f"   • 原版预估: {original_hours:.1f} 小时 ({original_hours/24:.1f} 天)")
    print(f"   • 多核版预估: {multicore_hours:.1f} 小时 ({multicore_hours/24:.1f} 天)")
    print(f"   • 节省时间: {original_hours - multicore_hours:.1f} 小时")


def main():
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 测试URL列表（使用更多产品进行准确测试）
    test_urls = [
        'https://www.traceparts.cn/en/product/the-timken-company-double-concentric-cartridge-block-qaamc10a050s?CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175',
        'https://www.traceparts.cn/en/product/ntn-europe-usc200t20-cartridge-unit-from-grey-cast-high-temperature?CatalogPath=TRACEPARTS%3ATP01002002006&Product=34-17112021-055894',
        'https://www.traceparts.cn/en/product/jw-winco-en-561-plastic-mounting-angle-brackets-type-b-and-c?CatalogPath=TRACEPARTS%3ATP05001&Product=90-05102020-040831',
        'https://www.traceparts.cn/en/product/essentra-components-male-locking-plate-mating-1600-series?CatalogPath=TRACEPARTS%3ATP04006002003001&Product=10-14072020-126290',
        'https://www.traceparts.cn/en/product/skf-2rs1-deep-groove-ball-bearing-basic-dynamic-load-rating-c-17-kn?CatalogPath=TRACEPARTS%3ATP01002001001&Product=10-11062021-035209',
        'https://www.traceparts.cn/en/product/skf-grease-standard-ball-bearing-unit-of-cast-iron-y-bearing-metric-thread-round-flange-syj-series?CatalogPath=TRACEPARTS%3ATP01002002002&Product=10-14012003-000965',
        'https://www.traceparts.cn/en/product/smc-round-cylinder-single-acting-spring-return-cd85n-series?CatalogPath=TRACEPARTS%3ATP02011001001&Product=10-04092019-113919',
        'https://www.traceparts.cn/en/product/skf-ball-screw-support-bearing-internal-clearance-cn-angular-contact-thrust-ball-bearings-basic-dynamic-load-rating-c-54-kn?CatalogPath=TRACEPARTS%3ATP01002001005&Product=10-11062021-035215',
    ]
    
    print(f"🧪 多核性能对比测试")
    print(f"📦 测试产品数: {len(test_urls)}")
    
    # 运行测试
    try:
        # 测试原版
        original_result = test_original_version(test_urls)
        
        # 等待一下，让系统恢复
        print("\n⏳ 等待5秒...")
        time.sleep(5)
        
        # 测试多核版
        multicore_result = test_multicore_version(test_urls)
        
        # 对比结果
        compare_results(original_result, multicore_result)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main() 