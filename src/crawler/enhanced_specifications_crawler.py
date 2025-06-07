#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版产品规格爬取器
=================
整合所有解决方案的最终版本
"""

import time
import logging
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from pathlib import Path
import sys

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.crawler.adaptive_specs_parser import AdaptiveSpecsParser
from src.utils.smart_waiter import SmartWaiter
from src.utils.anti_detection import AntiDetectionManager
from src.utils.smart_thread_pool import SmartThreadPool, Task, TaskPriority


class EnhancedSpecificationsCrawler:
    """增强版规格爬取器"""
    
    def __init__(self, max_workers: int = 12, log_level: int = logging.INFO):
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # 核心组件
        self.adaptive_parser = AdaptiveSpecsParser(self.logger)
        self.anti_detection = AntiDetectionManager(self.logger)
        self.thread_pool = SmartThreadPool(max_workers, self.logger)
        
        # 统计信息
        self.stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'vendor_breakdown': {},
            'error_categories': {}
        }
    
    def extract_batch_specifications(self, product_urls: List[str]) -> Dict[str, Any]:
        """批量提取产品规格 - 增强版"""
        if not product_urls:
            return {'results': [], 'summary': {}}
        
        self.logger.info(f"🚀 开始增强版批量规格提取")
        self.logger.info(f"   📦 产品数量: {len(product_urls)}")
        self.logger.info(f"   🧵 最大并发: {self.max_workers}")
        
        start_time = time.time()
        results = []
        futures = []
        
        # 创建任务并提交
        for i, url in enumerate(product_urls):
            vendor = self.anti_detection.detect_vendor_from_url(url)
            
            # 根据供应商设置优先级
            if vendor == 'apostoli':
                priority = TaskPriority.HIGH  # apostoli成功率高，优先处理
            elif vendor == 'industrietechnik':
                priority = TaskPriority.NORMAL  # industrietechnik需要特殊处理
            else:
                priority = TaskPriority.NORMAL
            
            task = Task(
                id=f"spec_{i}",
                url=url,
                vendor=vendor,
                priority=priority
            )
            
            # 提交任务
            future = self.thread_pool.submit_task(task, self._process_single_product)
            futures.append(future)
        
        # 收集结果
        for future in futures:
            try:
                result = future.result(timeout=60)  # 每个任务最多等待60秒
                results.append(result['result'] if result['success'] else {
                    'product_url': result.get('task_id', 'unknown'),
                    'specifications': [],
                    'count': 0,
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                })
            except Exception as e:
                self.logger.error(f"❌ 任务结果获取失败: {e}")
                results.append({
                    'product_url': 'unknown',
                    'specifications': [],
                    'count': 0,
                    'success': False,
                    'error': str(e)
                })
        
        # 等待所有任务完成
        self.thread_pool.wait_for_completion(timeout=300)
        
        # 统计结果
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r.get('success', False))
        total_specs = sum(r.get('count', 0) for r in results)
        
        # 获取性能统计
        pool_stats = self.thread_pool.get_performance_stats()
        
        self.logger.info(f"✅ 批量处理完成:")
        self.logger.info(f"   ⏱️  总耗时: {total_time:.1f}s")
        self.logger.info(f"   📊 成功率: {success_count}/{len(product_urls)} ({success_count/len(product_urls)*100:.1f}%)")
        self.logger.info(f"   📋 总规格数: {total_specs}")
        self.logger.info(f"   🧵 线程池统计: {pool_stats}")
        
        return {
            'results': results,
            'summary': {
                'total_products': len(product_urls),
                'successful_products': success_count,
                'failed_products': len(product_urls) - success_count,
                'total_specifications': total_specs,
                'processing_time': total_time,
                'success_rate': success_count / len(product_urls) if product_urls else 0,
                'avg_time_per_product': total_time / len(product_urls) if product_urls else 0,
                'thread_pool_stats': pool_stats
            }
        }
    
    def _process_single_product(self, task: Task, thread_resources: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个产品 - 使用线程资源"""
        try:
            driver = thread_resources['driver']
            waiter = thread_resources['waiter']
            anti_detection = thread_resources['anti_detection']
            
            self.logger.debug(f"🔍 处理产品: {task.url}")
            
            # 应用请求限流
            anti_detection.apply_request_throttling(task.vendor)
            
            # 访问页面
            driver.get(task.url)
            
            # 智能等待页面就绪
            page_ready = waiter.wait_for_page_ready(task.vendor)
            if not page_ready:
                self.logger.warning(f"⚠️ 页面未就绪: {task.url}")
            
            # 模拟人类行为
            anti_detection.simulate_human_behavior(driver)
            
            # 等待规格数据
            specs_ready = waiter.adaptive_wait_for_specs(task.vendor)
            if not specs_ready:
                self.logger.warning(f"⚠️ 规格数据未就绪: {task.url}")
            
            # 使用自适应解析器提取规格
            specifications = self.adaptive_parser.parse_specifications(driver, task.url)
            
            # 记录结果
            success = len(specifications) > 0
            
            if success:
                self.logger.info(f"✅ 规格提取成功: {task.url} -> {len(specifications)} 规格")
            else:
                self.logger.warning(f"❌ 规格提取失败: {task.url} -> 0 规格")
            
            # 直接返回adaptive_parser提取的规格数据（已经是test-09-1兼容格式）
            return {
                'product_url': task.url,
                'specifications': specifications,  # 直接使用adaptive_parser的结果
                'count': len(specifications),
                'success': success,
                'vendor': task.vendor,
                'page_type': self.adaptive_parser.detect_page_type(task.url, driver),
                'extraction_method': 'enhanced_adaptive'
            }
            
        except Exception as e:
            self.logger.error(f"❌ 产品处理异常: {task.url} - {e}")
            return {
                'product_url': task.url,
                'specifications': [],
                'count': 0,
                'success': False,
                'error': str(e),
                'vendor': task.vendor
            }
    
    def extract_specifications(self, product_url: str) -> Dict[str, Any]:
        """单产品提取接口 - 直接同步处理，避免双层并发冲突"""
        try:
            self.logger.debug(f"🔍 开始处理单个产品: {product_url}")
            
            # 检测供应商
            vendor = self.anti_detection.detect_vendor_from_url(product_url)
            
            # 应用请求限流（同步版本）
            self.anti_detection.apply_request_throttling(vendor)
            
            # 创建临时driver（简单同步模式）
            from selenium.webdriver.chrome.options import Options
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            driver = webdriver.Chrome(options=options)
            
            try:
                # 访问页面
                driver.get(product_url)
                
                # 创建临时waiter
                waiter = SmartWaiter(driver, self.logger)
                
                # 智能等待页面就绪
                page_ready = waiter.wait_for_page_ready(vendor)
                if not page_ready:
                    self.logger.warning(f"⚠️ 页面未就绪: {product_url}")
                
                # 模拟人类行为
                self.anti_detection.simulate_human_behavior(driver)
                
                # 等待规格数据
                specs_ready = waiter.adaptive_wait_for_specs(vendor)
                if not specs_ready:
                    self.logger.warning(f"⚠️ 规格数据未就绪: {product_url}")
                
                # 使用自适应解析器提取规格（test-09-1逻辑）
                specifications = self.adaptive_parser.parse_specifications(driver, product_url)
                
                # 记录结果
                success = len(specifications) > 0
                
                if success:
                    self.logger.debug(f"✅ 规格提取成功: {product_url} -> {len(specifications)} 规格")
                else:
                    self.logger.debug(f"❌ 规格提取失败: {product_url} -> 0 规格")
                
                # 返回与test-09-1兼容的格式
                return {
                    'product_url': product_url,
                    'specifications': specifications,  # AdaptiveSpecsParser已返回test-09-1格式
                    'count': len(specifications),
                    'success': success,
                    'vendor': vendor,
                    'page_type': self.adaptive_parser.detect_page_type(product_url, driver),
                    'extraction_method': 'enhanced_adaptive_sync'
                }
                
            finally:
                driver.quit()
                
        except Exception as e:
            self.logger.error(f"❌ 单产品处理异常: {product_url} - {e}")
            return {
                'product_url': product_url,
                'specifications': [],
                'count': 0,
                'success': False,
                'error': str(e),
                'vendor': self.anti_detection.detect_vendor_from_url(product_url)
            }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        pool_stats = self.thread_pool.get_performance_stats()
        
        return {
            'crawler_stats': self.stats,
            'thread_pool_stats': pool_stats,
            'timestamp': time.time()
        }
    
    def close(self):
        """关闭爬取器"""
        self.logger.info("🛑 关闭增强版规格爬取器...")
        self.thread_pool.shutdown()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """测试入口"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    # 测试URL
    test_urls = [
        'https://www.traceparts.cn/en/product/item-industrietechnik-gmbh-stairway-assembly-set-pp-30deg?CatalogPath=TRACEPARTS%3ATP12002018002&Product=30-12112020-084493',
        'https://www.traceparts.cn/en/product/apostoli-f30?CatalogPath=TRACEPARTS%3ATP12002018003004&Product=90-23112023-059945'
    ]
    
    with EnhancedSpecificationsCrawler(max_workers=4) as crawler:
        results = crawler.extract_batch_specifications(test_urls)
        
        print("\n" + "="*60)
        print("📊 测试结果摘要")
        print("="*60)
        
        summary = results['summary']
        print(f"总产品数: {summary['total_products']}")
        print(f"成功: {summary['successful_products']}")
        print(f"失败: {summary['failed_products']}")
        print(f"成功率: {summary['success_rate']:.1%}")
        print(f"总规格数: {summary['total_specifications']}")
        print(f"处理时间: {summary['processing_time']:.1f}s")


if __name__ == '__main__':
    main()