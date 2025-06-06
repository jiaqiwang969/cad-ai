#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试实时规格提取功能 - 性能分析版
准确测量各个环节的耗时，找出性能瓶颈
"""

import sys
import logging
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipelines.cache_manager import CacheManager, CacheLevel

class PerformanceTimer:
    """性能计时器"""
    def __init__(self):
        self.timings = {}
        self.current_section = None
        self.start_time = None
    
    def start(self, section_name):
        """开始计时"""
        if self.current_section:
            self.end()
        self.current_section = section_name
        self.start_time = time.time()
        print(f"⏱️  [{datetime.now().strftime('%H:%M:%S')}] 开始: {section_name}")
    
    def end(self):
        """结束当前计时"""
        if self.current_section:
            elapsed = time.time() - self.start_time
            self.timings[self.current_section] = elapsed
            print(f"⏱️  [{datetime.now().strftime('%H:%M:%S')}] 完成: {self.current_section} ({elapsed:.2f}秒)")
            self.current_section = None
    
    def report(self):
        """生成报告"""
        print("\n" + "="*60)
        print("📊 性能分析报告")
        print("="*60)
        total_time = sum(self.timings.values())
        for section, elapsed in sorted(self.timings.items(), key=lambda x: x[1], reverse=True):
            percentage = (elapsed / total_time * 100) if total_time > 0 else 0
            print(f"{section:.<40} {elapsed:6.2f}秒 ({percentage:5.1f}%)")
        print("-"*60)
        print(f"{'总计':.<40} {total_time:6.2f}秒")
        print("="*60)

def main():
    timer = PerformanceTimer()
    
    # 设置日志级别为 WARNING，减少日志输出
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    timer.start("1. 初始化")
    
    # 创建缓存管理器（限制并发数便于观察）
    cache_manager = CacheManager(cache_dir='results/cache_test_perf', max_workers=3)
    
    # 测试数据：使用3个产品URL
    test_products = [
        {
            'product_url': 'https://www.traceparts.cn/en/product/the-timken-company-double-concentric-cartridge-block-qaamc10a050s?CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175',
            'leaf_code': 'TEST001'
        },
        {
            'product_url': 'https://www.traceparts.cn/en/product/ntn-europe-usc200t20-cartridge-unit-from-grey-cast-high-temperature?CatalogPath=TRACEPARTS%3ATP01002002006&Product=34-17112021-055894',
            'leaf_code': 'TEST002'
        },
        {
            'product_url': 'https://www.traceparts.cn/en/product/jw-winco-en-561-plastic-mounting-angle-brackets-type-b-and-c?CatalogPath=TRACEPARTS%3ATP05001&Product=90-05102020-040831',
            'leaf_code': 'TEST003'
        }
    ]
    
    # 构造测试数据结构
    test_data = {
        'root': {
            'name': 'TraceParts',
            'code': 'ROOT',
            'url': 'https://www.traceparts.cn',
            'children': [],
            'is_leaf': False
        },
        'leaves': [
            {
                'code': 'TEST001',
                'name': 'Test Category 1',
                'products': [test_products[0]],
                'is_leaf': True
            },
            {
                'code': 'TEST002', 
                'name': 'Test Category 2',
                'products': [test_products[1]],
                'is_leaf': True
            },
            {
                'code': 'TEST003',
                'name': 'Test Category 3',
                'products': [test_products[2]],
                'is_leaf': True
            }
        ]
    }
    
    timer.end()  # 结束初始化
    
    print(f"\n🧪 性能分析测试")
    print(f"📁 缓存目录: {cache_manager.specs_cache_dir}")
    print(f"🔢 测试产品数: {len(test_products)}")
    print(f"⚙️  并发线程数: {cache_manager.max_workers}")
    print("="*60)
    
    # 测试单个产品提取（串行）
    print(f"\n📏 测试1: 串行提取（基准测试）")
    print("-"*60)
    
    # 导入爬虫模块
    from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
    crawler = OptimizedSpecificationsCrawler(log_level=logging.WARNING)
    
    serial_results = []
    timer.start("2. 串行提取总计")
    
    for i, product in enumerate(test_products):
        timer.start(f"2.{i+1} 产品{i+1} - 总计")
        
        timer.start(f"2.{i+1}.1 创建driver")
        driver = crawler._create_optimized_driver()
        timer.end()
        
        timer.start(f"2.{i+1}.2 页面加载")
        driver.get(product['product_url'])
        timer.end()
        
        timer.start(f"2.{i+1}.3 弹窗处理")
        crawler._close_disclaimer_popup(driver)
        timer.end()
        
        timer.start(f"2.{i+1}.4 设置分页")
        crawler._set_items_per_page_to_all(driver)
        timer.end()
        
        timer.start(f"2.{i+1}.5 页面滚动")
        crawler._scroll_page_fully(driver)
        timer.end()
        
        timer.start(f"2.{i+1}.6 提取规格")
        specs = crawler._extract_all_specifications(driver)
        timer.end()
        
        timer.start(f"2.{i+1}.7 关闭driver")
        driver.quit()
        timer.end()
        
        timer.end()  # 结束单个产品
        
        serial_results.append(len(specs))
        print(f"   产品{i+1}: {len(specs)} 个规格")
    
    timer.end()  # 结束串行提取
    
    # 测试并行提取
    print(f"\n🚀 测试2: 并行提取（当前实现）")
    print("-"*60)
    
    timer.start("3. 并行提取总计")
    try:
        # 清理缓存目录
        import shutil
        if cache_manager.specs_cache_dir.exists():
            shutil.rmtree(cache_manager.specs_cache_dir)
        cache_manager.specs_cache_dir.mkdir(parents=True, exist_ok=True)
        
        result = cache_manager.extend_to_specifications(test_data)
        timer.end()
        
        # 检查结果
        spec_files = list(cache_manager.specs_cache_dir.glob("*.json"))
        print(f"   生成文件数: {len(spec_files)}")
        
    except Exception as e:
        timer.end()
        print(f"   ❌ 测试失败: {e}")
    
    # 测试批量提取API
    print(f"\n⚡ 测试3: 批量API（extract_batch_specifications）")
    print("-"*60)
    
    timer.start("4. 批量API总计")
    product_urls = [p['product_url'] for p in test_products]
    batch_result = crawler.extract_batch_specifications(product_urls, max_workers=3)
    timer.end()
    
    print(f"   成功数: {batch_result['summary']['success_cnt']}")
    print(f"   总规格: {batch_result['summary']['total_specs']}")
    
    # 生成性能报告
    timer.report()
    
    # 性能优化建议
    print("\n💡 性能优化建议")
    print("="*60)
    
    # 分析driver创建时间
    driver_times = [v for k, v in timer.timings.items() if '创建driver' in k]
    if driver_times:
        avg_driver_time = sum(driver_times) / len(driver_times)
        print(f"1. Driver创建平均耗时: {avg_driver_time:.2f}秒")
        if avg_driver_time > 2:
            print("   ⚠️  Driver创建较慢，建议：")
            print("   - 使用driver池复用")
            print("   - 预创建driver实例")
            print("   - 考虑使用更轻量的浏览器选项")
    
    # 分析页面加载时间
    load_times = [v for k, v in timer.timings.items() if '页面加载' in k]
    if load_times:
        avg_load_time = sum(load_times) / len(load_times)
        print(f"\n2. 页面加载平均耗时: {avg_load_time:.2f}秒")
        if avg_load_time > 5:
            print("   ⚠️  页面加载较慢，建议：")
            print("   - 禁用更多资源（CSS、字体等）")
            print("   - 使用 page_load_strategy='eager'")
            print("   - 考虑使用请求拦截")
    
    # 分析提取时间
    extract_times = [v for k, v in timer.timings.items() if '提取规格' in k]
    if extract_times:
        avg_extract_time = sum(extract_times) / len(extract_times)
        print(f"\n3. 规格提取平均耗时: {avg_extract_time:.2f}秒")
        if avg_extract_time > 10:
            print("   ⚠️  提取过程较慢，建议：")
            print("   - 优化DOM查询选择器")
            print("   - 减少不必要的等待")
            print("   - 使用更高效的文本提取方法")
    
    # 计算并行加速比
    if '2. 串行提取总计' in timer.timings and '3. 并行提取总计' in timer.timings:
        serial_time = timer.timings['2. 串行提取总计']
        parallel_time = timer.timings['3. 并行提取总计']
        speedup = serial_time / parallel_time if parallel_time > 0 else 0
        print(f"\n4. 并行加速比: {speedup:.2f}x")
        if speedup < 2:
            print("   ⚠️  并行效果不理想，建议：")
            print("   - 增加并发数")
            print("   - 优化线程调度")
            print("   - 考虑异步IO")

if __name__ == '__main__':
    main() 