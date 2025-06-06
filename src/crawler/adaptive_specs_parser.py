#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应规格解析器
==============
根据页面结构自动选择最佳解析策略
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class AdaptiveSpecsParser:
    """自适应规格解析器"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # 解析策略库
        self.strategies = {
            'industrietechnik': self._parse_industrietechnik_style,
            'apostoli': self._parse_apostoli_style,
            'standard_table': self._parse_standard_table,
            'ajax_dynamic': self._parse_ajax_dynamic,
            'generic': self._parse_generic_fallback
        }
        
        # 页面特征识别器
        self.page_patterns = {
            'industrietechnik': [
                r'item-industrietechnik-gmbh',
                r'Product=30-\d+-\d+'
            ],
            'apostoli': [
                r'apostoli',
                r'Product=90-\d+-\d+'
            ]
        }
    
    def detect_page_type(self, url: str, driver) -> str:
        """检测页面类型"""
        try:
            # URL模式检测
            for page_type, patterns in self.page_patterns.items():
                if any(re.search(pattern, url) for pattern in patterns):
                    self.logger.debug(f"🔍 URL模式检测: {page_type}")
                    return page_type
            
            # DOM结构检测
            page_source = driver.page_source
            
            # 检测特定供应商标识
            if 'industrietechnik' in page_source.lower():
                return 'industrietechnik'
            elif 'apostoli' in page_source.lower():
                return 'apostoli'
            
            # 检测表格结构
            tables = driver.find_elements(By.TAG_NAME, 'table')
            if len(tables) > 0:
                return 'standard_table'
            
            # 检测AJAX加载
            if 'data-' in page_source or 'ng-' in page_source:
                return 'ajax_dynamic'
                
        except Exception as e:
            self.logger.warning(f"页面类型检测失败: {e}")
        
        return 'generic'
    
    def parse_specifications(self, driver, url: str) -> List[Dict[str, Any]]:
        """根据页面类型自适应解析规格"""
        page_type = self.detect_page_type(url, driver)
        strategy = self.strategies.get(page_type, self.strategies['generic'])
        
        self.logger.info(f"🎯 使用解析策略: {page_type}")
        
        try:
            return strategy(driver, url)
        except Exception as e:
            self.logger.warning(f"策略 {page_type} 失败，尝试通用策略: {e}")
            return self.strategies['generic'](driver, url)
    
    def _parse_industrietechnik_style(self, driver, url: str) -> List[Dict[str, Any]]:
        """专门处理industrietechnik页面结构"""
        self.logger.debug("🔧 使用industrietechnik专用解析")
        
        specifications = []
        
        try:
            # 等待更长时间，industrietechnik页面加载较慢
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)  # 额外等待
            
            # 查找industrietechnik特有的规格容器
            spec_selectors = [
                "//div[contains(@class, 'product-specifications')]",
                "//div[contains(@class, 'technical-data')]", 
                "//div[contains(@class, 'product-details')]",
                "//table[contains(@class, 'spec-table')]",
                "//div[@id='specifications']",
                "//div[@id='technical-data']"
            ]
            
            for selector in spec_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        self.logger.debug(f"✅ 找到规格容器: {selector}")
                        # 提取规格数据
                        specs = self._extract_from_container(elements[0])
                        if specs:
                            specifications.extend(specs)
                            break
                except Exception as e:
                    self.logger.debug(f"选择器失败 {selector}: {e}")
                    continue
            
            # 如果还是没找到，尝试更宽泛的搜索
            if not specifications:
                self.logger.debug("🔍 尝试宽泛搜索...")
                specifications = self._broad_search_specs(driver)
                
        except Exception as e:
            self.logger.error(f"industrietechnik解析失败: {e}")
        
        return specifications
    
    def _parse_apostoli_style(self, driver, url: str) -> List[Dict[str, Any]]:
        """专门处理apostoli页面结构"""
        self.logger.debug("🎨 使用apostoli专用解析")
        
        # apostoli页面通常有标准表格结构
        return self._parse_standard_table(driver, url)
    
    def _parse_standard_table(self, driver, url: str) -> List[Dict[str, Any]]:
        """标准表格解析"""
        specifications = []
        
        try:
            tables = driver.find_elements(By.TAG_NAME, 'table')
            
            for table in tables:
                if not table.is_displayed():
                    continue
                    
                rows = table.find_elements(By.TAG_NAME, 'tr')
                if len(rows) < 2:  # 至少需要标题行和数据行
                    continue
                
                # 提取表格数据
                table_specs = self._extract_table_specs(table)
                specifications.extend(table_specs)
                
        except Exception as e:
            self.logger.error(f"标准表格解析失败: {e}")
        
        return specifications
    
    def _parse_ajax_dynamic(self, driver, url: str) -> List[Dict[str, Any]]:
        """处理AJAX动态加载页面"""
        self.logger.debug("⏳ 处理AJAX动态页面")
        
        try:
            # 等待动态内容加载
            WebDriverWait(driver, 15).until(
                lambda d: len(d.find_elements(By.TAG_NAME, 'table')) > 0 or
                         len(d.find_elements(By.XPATH, "//div[contains(@class, 'spec')]")) > 0
            )
            time.sleep(2)  # 额外缓冲
            
            # 尝试触发更多内容加载
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            return self._parse_standard_table(driver, url)
            
        except Exception as e:
            self.logger.warning(f"AJAX页面处理失败: {e}")
            return []
    
    def _parse_generic_fallback(self, driver, url: str) -> List[Dict[str, Any]]:
        """通用后备解析策略"""
        self.logger.debug("🛡️ 使用通用后备解析")
        
        specifications = []
        
        try:
            # 多种搜索策略
            search_strategies = [
                self._find_by_keywords,
                self._find_by_structure,
                self._find_by_tables,
                self._find_by_lists
            ]
            
            for strategy in search_strategies:
                try:
                    specs = strategy(driver)
                    if specs:
                        specifications.extend(specs)
                        break
                except Exception as e:
                    self.logger.debug(f"后备策略失败: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"通用解析失败: {e}")
        
        return specifications
    
    def _extract_from_container(self, container) -> List[Dict[str, Any]]:
        """从容器中提取规格数据"""
        specifications = []
        
        try:
            # 查找表格
            tables = container.find_elements(By.TAG_NAME, 'table')
            for table in tables:
                specs = self._extract_table_specs(table)
                specifications.extend(specs)
            
            # 查找键值对
            if not specifications:
                kvp_elements = container.find_elements(By.XPATH, ".//div[contains(@class, 'spec-item')]")
                for elem in kvp_elements:
                    spec = self._extract_key_value_pair(elem)
                    if spec:
                        specifications.append(spec)
                        
        except Exception as e:
            self.logger.debug(f"容器提取失败: {e}")
        
        return specifications
    
    def _extract_table_specs(self, table) -> List[Dict[str, Any]]:
        """从表格提取规格"""
        specifications = []
        
        try:
            rows = table.find_elements(By.TAG_NAME, 'tr')
            if len(rows) < 2:
                return []
            
            # 获取表头
            header_row = rows[0]
            headers = [th.text.strip() for th in header_row.find_elements(By.TAG_NAME, 'th')]
            if not headers:
                headers = [td.text.strip() for td in header_row.find_elements(By.TAG_NAME, 'td')]
            
            # 处理数据行
            for row in rows[1:]:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) < 2:
                    continue
                
                cell_texts = [cell.text.strip() for cell in cells]
                
                # 构建规格字典
                spec = {}
                for i, cell_text in enumerate(cell_texts):
                    if i < len(headers) and headers[i] and cell_text:
                        spec[headers[i]] = cell_text
                
                if len(spec) >= 2:  # 至少要有2个有效字段
                    specifications.append(spec)
                    
        except Exception as e:
            self.logger.debug(f"表格规格提取失败: {e}")
        
        return specifications
    
    def _extract_key_value_pair(self, element) -> Optional[Dict[str, Any]]:
        """提取键值对"""
        try:
            text = element.text.strip()
            if ':' in text:
                parts = text.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        return {key: value}
        except Exception as e:
            self.logger.debug(f"键值对提取失败: {e}")
        
        return None
    
    def _broad_search_specs(self, driver) -> List[Dict[str, Any]]:
        """宽泛搜索规格信息"""
        specifications = []
        
        try:
            # 搜索包含规格关键词的元素
            spec_keywords = ['specification', 'technical', 'dimension', 'parameter', 'property']
            
            for keyword in spec_keywords:
                try:
                    elements = driver.find_elements(By.XPATH, 
                        f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]")
                    
                    for elem in elements:
                        # 在元素附近查找表格或结构化数据
                        parent = elem.find_element(By.XPATH, "./..")
                        tables = parent.find_elements(By.TAG_NAME, 'table')
                        
                        for table in tables:
                            specs = self._extract_table_specs(table)
                            specifications.extend(specs)
                            
                        if specifications:
                            break
                    
                    if specifications:
                        break
                        
                except Exception as e:
                    self.logger.debug(f"关键词搜索失败 {keyword}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.debug(f"宽泛搜索失败: {e}")
        
        return specifications
    
    def _find_by_keywords(self, driver) -> List[Dict[str, Any]]:
        """通过关键词查找"""
        return self._broad_search_specs(driver)
    
    def _find_by_structure(self, driver) -> List[Dict[str, Any]]:
        """通过结构查找"""
        specifications = []
        
        try:
            # 查找常见的规格容器结构
            containers = driver.find_elements(By.XPATH, 
                "//div[contains(@class, 'spec') or contains(@class, 'technical') or contains(@class, 'detail')]")
            
            for container in containers:
                specs = self._extract_from_container(container)
                specifications.extend(specs)
                
        except Exception as e:
            self.logger.debug(f"结构查找失败: {e}")
        
        return specifications
    
    def _find_by_tables(self, driver) -> List[Dict[str, Any]]:
        """通过表格查找"""
        return self._parse_standard_table(driver, "")
    
    def _find_by_lists(self, driver) -> List[Dict[str, Any]]:
        """通过列表查找"""
        specifications = []
        
        try:
            lists = driver.find_elements(By.TAG_NAME, 'ul')
            lists.extend(driver.find_elements(By.TAG_NAME, 'ol'))
            
            for list_elem in lists:
                items = list_elem.find_elements(By.TAG_NAME, 'li')
                for item in items:
                    spec = self._extract_key_value_pair(item)
                    if spec:
                        specifications.append(spec)
                        
        except Exception as e:
            self.logger.debug(f"列表查找失败: {e}")
        
        return specifications