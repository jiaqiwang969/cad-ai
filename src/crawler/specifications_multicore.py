#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多核优化版产品规格爬取模块
=========================
针对多核CPU优化，提供更好的并发性能
保持数据完整性，不丢失任何规格信息
"""

import re
import time
import threading
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from config.settings import Settings
from config.logging_config import LoggerMixin
from src.utils.browser_manager import create_browser_manager
from src.utils.net_guard import register_success, register_fail


class MultiCoreSpecificationsCrawler(LoggerMixin):
    """多核优化的产品规格爬取器"""
    
    def __init__(self, max_workers: int = None, browser_pool_size: int = None):
        """
        初始化多核规格爬取器
        
        Args:
            max_workers: 最大工作线程数（默认使用CPU核心数）
            browser_pool_size: 浏览器池大小（默认为 max_workers * 1.5）
        """
        import os
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) * 2)
        self.browser_pool_size = browser_pool_size or int(self.max_workers * 1.5)
        
        # 创建更大的浏览器池
        self.browser_manager = create_browser_manager(
            browser_type='selenium',
            pool_size=self.browser_pool_size
        )
        
        # 性能统计
        self.stats = {
            'total_processed': 0,
            'success_count': 0,
            'fail_count': 0,
            'total_specs': 0,
            'start_time': None,
            'lock': threading.Lock()
        }
        
        # 动态超时管理
        self.timeout_manager = DynamicTimeoutManager()
        
        self.logger.info(f"多核爬虫初始化: workers={self.max_workers}, pool={self.browser_pool_size}")
    
    def _is_valid_product_reference(self, text: str) -> bool:
        """检查是否为有效的产品参考号（与原版相同）"""
        if not text or len(text) < 3:
            return False
        
        exclude_keywords = [
            'aluminum', 'description', 'links', 
            'manufacturer', 'product page', 'material',
            'weight', 'dimension', 'color'
        ]
        
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in exclude_keywords):
            return False
        
        has_letter = bool(re.search(r'[A-Za-z]', text))
        has_number = bool(re.search(r'\d', text))
        
        if len(text) > 60:
            return False
        
        return has_letter and has_number
    
    def _smart_wait_for_content(self, driver, timeout: int = None) -> bool:
        """智能等待页面内容加载"""
        timeout = timeout or self.timeout_manager.get_timeout()
        
        try:
            # 等待主要内容容器
            wait = WebDriverWait(driver, timeout)
            
            # 策略1：等待表格出现
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table, .table')))
                return True
            except TimeoutException:
                pass
            
            # 策略2：等待产品信息容器
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[class*="product"], [class*="spec"]')))
                return True
            except TimeoutException:
                pass
            
            # 策略3：等待任何表格行
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, 'tr')))
                return True
            except TimeoutException:
                pass
            
            return False
            
        except Exception as e:
            self.logger.debug(f"智能等待失败: {e}")
            return False
    
    def _optimized_scroll(self, driver):
        """优化的滚动策略"""
        # 使用更快的滚动方式
        driver.execute_script("""
            // 快速滚动到底部
            window.scrollTo(0, document.body.scrollHeight);
            
            // 触发懒加载
            var event = new Event('scroll');
            window.dispatchEvent(event);
        """)
        
        # 只等待必要的时间
        time.sleep(0.5)
        
        # 检查是否有新内容加载
        new_height = driver.execute_script("return document.body.scrollHeight")
        return new_height
    
    def _parallel_extract_specifications(self, product_url: str) -> Dict[str, Any]:
        """并行提取单个产品的规格"""
        start_time = time.time()
        
        with self.browser_manager.get_browser() as driver:
            try:
                # 访问页面
                driver.get(product_url)
                
                # 智能等待内容加载
                if not self._smart_wait_for_content(driver):
                    self.logger.warning(f"页面内容加载失败: {product_url}")
                    return self._create_result(product_url, [], False, "content_load_failed")
                
                # 尝试点击"显示全部"（使用更快的方法）
                self._quick_click_show_all(driver)
                
                # 优化滚动
                self._optimized_scroll(driver)
                
                # 提取规格
                specifications = self._extract_specifications_from_page(driver)
                
                # 更新统计
                self._update_stats(True, len(specifications))
                
                # 记录响应时间供动态超时使用
                response_time = time.time() - start_time
                self.timeout_manager.record_response_time(response_time)
                
                self.logger.info(f"✅ 提取成功: {len(specifications)} 个规格 ({response_time:.1f}秒) - {product_url}")
                register_success()
                
                return self._create_result(product_url, specifications, True)
                
            except Exception as e:
                self._update_stats(False, 0)
                self.logger.error(f"❌ 提取失败: {e} - {product_url}")
                register_fail('extraction_error')
                return self._create_result(product_url, [], False, str(e))
    
    def _quick_click_show_all(self, driver):
        """快速点击显示全部按钮"""
        try:
            # 使用 JavaScript 直接点击，避免滚动和等待
            driver.execute_script("""
                var buttons = document.querySelectorAll('*');
                for (var i = 0; i < buttons.length; i++) {
                    var btn = buttons[i];
                    if (btn.textContent.trim() === 'All' && 
                        (btn.tagName === 'BUTTON' || btn.tagName === 'LI' || 
                         btn.tagName === 'OPTION' || btn.tagName === 'DIV' || 
                         btn.tagName === 'SPAN')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            """)
            time.sleep(0.5)  # 短暂等待页面更新
        except:
            pass
    
    def _extract_specifications_from_page(self, driver) -> List[Dict[str, Any]]:
        """从页面提取规格信息"""
        specifications = []
        seen_references = set()
        
        # 批量获取所有行，减少 DOM 访问次数
        rows = driver.find_elements(By.CSS_SELECTOR, 'tr')
        
        for row in rows:
            try:
                # 批量获取单元格文本
                cell_texts = driver.execute_script("""
                    var cells = arguments[0].querySelectorAll('td, th');
                    return Array.from(cells).map(cell => cell.textContent.trim());
                """, row)
                
                # 查找产品参考号
                for i, text in enumerate(cell_texts[:5]):
                    if self._is_valid_product_reference(text) and text not in seen_references:
                        seen_references.add(text)
                        
                        spec = {
                            'reference': text,
                            'row_index': i,
                            'all_cells': cell_texts,
                            'cell_count': len(cell_texts)
                        }
                        
                        if len(cell_texts) > 1:
                            spec['description'] = cell_texts[1] if len(cell_texts) > 1 else ''
                            spec['details'] = cell_texts[2:] if len(cell_texts) > 2 else []
                        
                        specifications.append(spec)
                        break
                        
            except Exception as e:
                self.logger.debug(f"处理表格行时出错: {e}")
                continue
        
        return specifications
    
    def _create_result(self, product_url: str, specifications: List[Dict], 
                      success: bool, error: str = None) -> Dict[str, Any]:
        """创建统一的结果格式"""
        return {
            'product_url': product_url,
            'specifications': specifications,
            'count': len(specifications),
            'success': success,
            'error': error
        }
    
    def _update_stats(self, success: bool, spec_count: int):
        """线程安全地更新统计信息"""
        with self.stats['lock']:
            self.stats['total_processed'] += 1
            if success:
                self.stats['success_count'] += 1
                self.stats['total_specs'] += spec_count
            else:
                self.stats['fail_count'] += 1
    
    def extract_specifications(self, product_url: str) -> Dict[str, Any]:
        """提取单个产品规格（兼容接口）"""
        return self._parallel_extract_specifications(product_url)
    
    def extract_batch_specifications(self, product_urls: List[str], 
                                   max_workers: int = None) -> List[Dict[str, Any]]:
        """批量提取产品规格（多核优化版本）"""
        max_workers = max_workers or self.max_workers
        results = []
        total_urls = len(product_urls)
        
        self.logger.info(f"🚀 开始多核批量提取: {total_urls} 个产品, {max_workers} 个工作线程")
        self.stats['start_time'] = time.time()
        
        # 预热浏览器池
        self._preheat_browser_pool(min(max_workers, self.browser_pool_size))
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_url = {
                executor.submit(self._parallel_extract_specifications, url): url
                for url in product_urls
            }
            
            # 实时处理结果
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # 实时进度报告
                    with self.stats['lock']:
                        processed = self.stats['total_processed']
                        if processed % 100 == 0:
                            self._report_progress(processed, total_urls)
                            
                except Exception as e:
                    self.logger.error(f"任务异常: {e}")
                    results.append(self._create_result(url, [], False, str(e)))
        
        # 最终统计
        self._report_final_stats(total_urls)
        
        return results
    
    def _preheat_browser_pool(self, count: int):
        """预热浏览器池，减少启动延迟"""
        self.logger.info(f"预热浏览器池: {count} 个实例")
        
        def create_browser():
            with self.browser_manager.get_browser() as browser:
                # 访问空白页进行预热
                browser.get("about:blank")
                time.sleep(0.1)
        
        # 并行创建浏览器实例
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(create_browser) for _ in range(count)]
            for future in as_completed(futures):
                try:
                    future.result()
                except:
                    pass
    
    def _report_progress(self, processed: int, total: int):
        """报告进度"""
        elapsed = time.time() - self.stats['start_time']
        rate = processed / elapsed if elapsed > 0 else 0
        eta = (total - processed) / rate if rate > 0 else 0
        
        self.logger.info(
            f"📊 进度: {processed}/{total} ({processed*100/total:.1f}%) | "
            f"速度: {rate:.1f} 个/秒 | "
            f"预计剩余: {eta/60:.1f} 分钟"
        )
    
    def _report_final_stats(self, total_urls: int):
        """报告最终统计"""
        elapsed = time.time() - self.stats['start_time']
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"✅ 多核批量提取完成")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"📊 总体统计:")
        self.logger.info(f"   • 总产品数: {total_urls}")
        self.logger.info(f"   • 成功: {self.stats['success_count']} ({self.stats['success_count']*100/total_urls:.1f}%)")
        self.logger.info(f"   • 失败: {self.stats['fail_count']}")
        self.logger.info(f"   • 总规格数: {self.stats['total_specs']}")
        self.logger.info(f"   • 总耗时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
        self.logger.info(f"   • 平均速度: {total_urls/elapsed:.2f} 个/秒")
        self.logger.info(f"   • 平均每个产品: {elapsed/total_urls:.1f} 秒")
        self.logger.info(f"{'='*60}")


class DynamicTimeoutManager:
    """动态超时管理器"""
    
    def __init__(self, base_timeout: int = 30):
        self.base_timeout = base_timeout
        self.response_times = []
        self.lock = threading.Lock()
        self.max_samples = 100
    
    def record_response_time(self, time_seconds: float):
        """记录响应时间"""
        with self.lock:
            self.response_times.append(time_seconds)
            if len(self.response_times) > self.max_samples:
                self.response_times.pop(0)
    
    def get_timeout(self) -> int:
        """获取动态超时时间"""
        with self.lock:
            if not self.response_times:
                return self.base_timeout
            
            # 使用95分位数作为超时时间
            sorted_times = sorted(self.response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p95_time = sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]
            
            # 超时时间为 P95 的 1.5 倍，但不低于基础超时
            dynamic_timeout = max(self.base_timeout, int(p95_time * 1.5))
            
            return min(dynamic_timeout, 90)  # 最大90秒 