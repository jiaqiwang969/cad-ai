#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版产品规格爬取模块
====================
应用所有性能优化经验的产品规格爬取器
"""

import re
import time
import logging
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class OptimizedSpecificationsCrawler:
    """优化版产品规格爬取器"""
    
    # 预编译配置常量
    TIMEOUT = 60
    SCROLL_PAUSE = 1.3
    MAX_RETRY = 3
    MIN_REF_LENGTH = 3
    MAX_REF_LENGTH = 60
    
    # 排除的关键词
    EXCLUDE_KEYWORDS = [
        'aluminum', 'description', 'links', 
        'manufacturer', 'product page', 'material',
        'weight', 'dimension', 'color'
    ]
    
    def __init__(self, log_level: int = logging.INFO):
        """初始化优化版规格爬取器"""
        # 简单日志设置 (一次性)
        self.logger = logging.getLogger("opt-specifications")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            self.logger.addHandler(handler)
        self.logger.setLevel(log_level)
        # 防止日志向上传播，避免重复输出
        self.logger.propagate = False
        
        # 预编译正则表达式
        self.has_letter = re.compile(r'[A-Za-z]')
        self.has_number = re.compile(r'\d')
    
    def _create_optimized_driver(self):
        """创建优化的驱动"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(self.TIMEOUT)
        return driver
    
    def _is_valid_product_reference(self, text: str) -> bool:
        """检查是否为有效的产品参考号 (优化版)"""
        if not text or len(text) < self.MIN_REF_LENGTH:
            return False
        
        # 长度限制
        if len(text) > self.MAX_REF_LENGTH:
            return False
        
        # 快速检查排除关键词
        text_lower = text.lower()
        for keyword in self.EXCLUDE_KEYWORDS:
            if keyword in text_lower:
                return False
        
        # 必须包含字母和数字 (使用预编译的正则)
        has_letter = bool(self.has_letter.search(text))
        has_number = bool(self.has_number.search(text))
        
        return has_letter and has_number
    
    def _scroll_to_bottom(self, driver):
        """滚动到页面底部"""
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.SCROLL_PAUSE)
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            last_height = new_height
    
    def _click_show_all(self, driver) -> bool:
        """尝试点击"显示全部"按钮 (优化版)"""
        # 简化的选择器
        selectors = [
            "//li[text()='All']",
            "//option[text()='All']",
            "//button[text()='All']",
            "//div[contains(@class,'all')]"
        ]
        
        for selector in selectors:
            try:
                elem = driver.find_element(By.XPATH, selector)
                if elem.is_displayed() and elem.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    elem.click()
                    time.sleep(2)  # 等待页面更新
                    self.logger.debug("成功点击'All'按钮")
                    return True
            except:
                continue
        
        return False
    
    def _extract_specifications_once(self, product_url: str) -> List[Dict[str, Any]]:
        """单次尝试提取产品规格 (优化版)"""
        specifications = []
        seen_references = set()
        driver = None
        
        try:
            driver = self._create_optimized_driver()
            self.logger.debug(f"访问产品页面: {product_url}")
            driver.get(product_url)
            
            # 等待页面加载
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            
            # 等待内容加载
            time.sleep(2)
            
            # 尝试点击"显示全部"
            self._click_show_all(driver)
            
            # 滚动加载所有内容
            self._scroll_to_bottom(driver)
            
            # 使用JavaScript提取所有规格 (预编译)
            js_extract = """
            const specs = [];
            const seen = new Set();
            
            // 查找所有表格行
            const rows = document.querySelectorAll('tr');
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 2) {
                    const reference = cells[0].textContent.trim();
                    const description = cells[1].textContent.trim();
                    
                    if (reference && description && !seen.has(reference)) {
                        specs.push({
                            reference: reference,
                            description: description
                        });
                        seen.add(reference);
                    }
                }
            });
            
            return specs;
            """
            
            raw_specs = driver.execute_script(js_extract)
            
            # 过滤有效的规格
            for spec in raw_specs:
                if self._is_valid_product_reference(spec['reference']):
                    specifications.append({
                        'product_reference': spec['reference'],
                        'description': spec['description']
                    })
            
            self.logger.info(f"从 {product_url} 提取到 {len(specifications)} 个规格")
            
        except TimeoutException:
            self.logger.warning(f"页面加载超时: {product_url}")
            raise
        except Exception as e:
            self.logger.error(f"提取规格失败: {e}")
            raise
        finally:
            if driver:
                driver.quit()
        
        return specifications
    
    def extract_specifications(self, product_url: str) -> Dict[str, Any]:
        """提取产品规格（带重试）"""
        for attempt in range(1, self.MAX_RETRY + 1):
            try:
                specifications = self._extract_specifications_once(product_url)
                return {
                    'product_url': product_url,
                    'specifications': specifications,
                    'count': len(specifications),
                    'success': True
                }
                
            except (TimeoutException, Exception) as e:
                if attempt < self.MAX_RETRY:
                    self.logger.warning(f"尝试 {attempt}/{self.MAX_RETRY} 失败，重试: {product_url}")
                    time.sleep(2)
                else:
                    self.logger.error(f"达到最大重试次数，放弃: {product_url}")
                    
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
                                   max_workers: int = 16) -> List[Dict[str, Any]]:
        """批量提取产品规格 (简化版，串行处理)"""
        results = []
        total = len(product_urls)
        
        self.logger.info(f"开始批量提取 {total} 个产品的规格信息")
        
        for i, url in enumerate(product_urls):
            if i % 10 == 0:  # 每10个产品记录一次进度
                self.logger.info(f"进度: {i}/{total} ({i/total*100:.1f}%)")
            
            result = self.extract_specifications(url)
            results.append(result)
        
        # 统计
        success_count = sum(1 for r in results if r['success'])
        total_specs = sum(r['count'] for r in results)
        
        self.logger.info(
            f"批量提取完成: {success_count}/{total} 个产品成功, "
            f"共 {total_specs} 个规格"
        )
        
        return results 