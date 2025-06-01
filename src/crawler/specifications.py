#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
产品规格爬取模块
===============
负责从产品页面提取规格信息
"""

import re
import time
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from config.settings import Settings
from config.logging_config import LoggerMixin
from src.utils.browser_manager import create_browser_manager
from src.utils.net_guard import register_success, register_fail


class SpecificationsCrawler(LoggerMixin):
    """产品规格爬取器"""
    
    def __init__(self, browser_manager=None):
        """
        初始化规格爬取器
        
        Args:
            browser_manager: 浏览器管理器实例
        """
        self.browser_manager = browser_manager or create_browser_manager()
    
    def _is_valid_product_reference(self, text: str) -> bool:
        """
        检查是否为有效的产品参考号
        
        Args:
            text: 待检查的文本
            
        Returns:
            是否有效
        """
        if not text or len(text) < 3:
            return False
        
        # 排除的关键词
        exclude_keywords = [
            'aluminum', 'description', 'links', 
            'manufacturer', 'product page', 'material',
            'weight', 'dimension', 'color'
        ]
        
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in exclude_keywords):
            return False
        
        # 必须包含字母和数字
        has_letter = bool(re.search(r'[A-Za-z]', text))
        has_number = bool(re.search(r'\d', text))
        
        # 长度限制
        if len(text) > 60:
            return False
        
        return has_letter and has_number
    
    def _scroll_to_bottom(self, driver):
        """滚动到页面底部"""
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_pause = Settings.CRAWLER['scroll_pause']
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            last_height = new_height
    
    def _click_show_all(self, driver) -> bool:
        """
        尝试点击"显示全部"按钮
        
        Returns:
            是否成功点击
        """
        try:
            # 查找包含"All"文本的可点击元素
            all_buttons = driver.find_elements(
                By.XPATH,
                "//*[text()='All' and (self::li or self::option or self::div or self::span or self::button)]"
            )
            
            for button in all_buttons:
                try:
                    if button.is_displayed() and button.is_enabled():
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            button
                        )
                        button.click()
                        time.sleep(2)  # 等待页面更新
                        self.logger.debug("成功点击'All'按钮")
                        return True
                except:
                    continue
                    
        except Exception as e:
            self.logger.debug(f"点击'All'按钮时出错: {e}")
        
        return False
    
    def _extract_specifications_once(self, product_url: str) -> List[Dict[str, Any]]:
        """
        单次尝试提取产品规格
        
        Args:
            product_url: 产品URL
            
        Returns:
            规格列表
        """
        specifications = []
        seen_references = set()
        
        with self.browser_manager.get_browser() as driver:
            try:
                self.logger.debug(f"访问产品页面: {product_url}")
                driver.get(product_url)
                
                # 等待页面加载
                WebDriverWait(driver, Settings.CRAWLER['timeout']).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
                
                # 等待内容加载
                time.sleep(2)
                
                # 尝试点击"显示全部"
                self._click_show_all(driver)
                
                # 滚动加载所有内容
                self._scroll_to_bottom(driver)
                
                # 查找所有表格行
                rows = driver.find_elements(By.CSS_SELECTOR, 'tr')
                
                for row in rows:
                    try:
                        # 获取所有单元格
                        cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                        cell_texts = [cell.text.strip() for cell in cells]
                        
                        # 查找产品参考号（通常在前几列）
                        for i, text in enumerate(cell_texts[:5]):
                            if (self._is_valid_product_reference(text) and 
                                text not in seen_references):
                                
                                seen_references.add(text)
                                
                                # 构建规格信息
                                spec = {
                                    'reference': text,
                                    'row_index': i,
                                    'all_cells': cell_texts,
                                    'cell_count': len(cell_texts)
                                }
                                
                                # 尝试提取额外信息
                                if len(cell_texts) > 1:
                                    spec['description'] = cell_texts[1] if len(cell_texts) > 1 else ''
                                    spec['details'] = cell_texts[2:] if len(cell_texts) > 2 else []
                                
                                specifications.append(spec)
                                break
                                
                    except Exception as e:
                        self.logger.debug(f"处理表格行时出错: {e}")
                        continue
                
                self.logger.info(f"从 {product_url} 提取到 {len(specifications)} 个规格")
                register_success()
                
            except TimeoutException:
                self.logger.warning(f"页面加载超时: {product_url}")
                register_fail('timeout')
                raise
            except WebDriverException as e:
                self.logger.warning(f"浏览器异常: {e}")
                register_fail('browser')
                raise
            except Exception as e:
                self.logger.error(f"提取规格失败: {e}")
                register_fail('parse')
                raise
        
        return specifications
    
    def extract_specifications(self, product_url: str) -> Dict[str, Any]:
        """
        提取产品规格（带重试）
        
        Args:
            product_url: 产品URL
            
        Returns:
            包含产品URL和规格列表的字典
        """
        retry_strategy = Settings.get_retry_strategy('timeout_error')
        max_retry = retry_strategy['max_retry']
        
        for attempt in range(1, max_retry + 1):
            try:
                specifications = self._extract_specifications_once(product_url)
                return {
                    'product_url': product_url,
                    'specifications': specifications,
                    'count': len(specifications),
                    'success': True
                }
                
            except (TimeoutException, WebDriverException) as e:
                if attempt < max_retry:
                    delay = retry_strategy['delay'](attempt)
                    self.logger.warning(
                        f"尝试 {attempt}/{max_retry} 失败，{delay}秒后重试: {product_url}"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"达到最大重试次数，放弃: {product_url}")
                    
            except Exception as e:
                self.logger.error(f"意外错误: {e}")
                break
        
        # 返回失败结果
        return {
            'product_url': product_url,
            'specifications': [],
            'count': 0,
            'success': False,
            'error': 'retry_failed'
        }
    
    def extract_batch_specifications(self,
                                   product_urls: List[str],
                                   max_workers: int = None) -> List[Dict[str, Any]]:
        """
        批量提取产品规格
        
        Args:
            product_urls: 产品URL列表
            max_workers: 最大并发数
            
        Returns:
            规格信息列表
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        max_workers = max_workers or Settings.CRAWLER['max_workers']
        results = []
        
        self.logger.info(f"开始批量提取 {len(product_urls)} 个产品的规格信息")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_url = {
                executor.submit(self.extract_specifications, url): url
                for url in product_urls
            }
            
            # 收集结果
            completed = 0
            for future in as_completed(future_to_url):
                completed += 1
                url = future_to_url[future]
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        self.logger.info(
                            f"✅ [{completed}/{len(product_urls)}] "
                            f"提取成功: {result['count']} 个规格"
                        )
                    else:
                        self.logger.warning(
                            f"⚠️ [{completed}/{len(product_urls)}] "
                            f"提取失败: {url}"
                        )
                        
                except Exception as e:
                    self.logger.error(f"❌ [{completed}/{len(product_urls)}] 异常: {e}")
                    results.append({
                        'product_url': url,
                        'specifications': [],
                        'count': 0,
                        'success': False,
                        'error': str(e)
                    })
        
        # 统计
        success_count = sum(1 for r in results if r['success'])
        total_specs = sum(r['count'] for r in results)
        
        self.logger.info(
            f"批量提取完成: {success_count}/{len(product_urls)} 个产品成功, "
            f"共 {total_specs} 个规格"
        )
        
        return results 