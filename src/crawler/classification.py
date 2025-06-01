#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类树爬取模块
=============
负责爬取TraceParts的分类树结构
"""

import re
import time
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config.settings import Settings
from config.logging_config import LoggerMixin
from src.utils.browser_manager import create_browser_manager
from src.utils.net_guard import register_success, register_fail


class ClassificationCrawler(LoggerMixin):
    """分类树爬取器"""
    
    # 排除的链接模式
    EXCLUDE_PATTERNS = [
        "sign-in", "sign-up", "login", "register",
        "javascript:", "mailto:", "#"
    ]
    
    def __init__(self, browser_manager=None):
        """
        初始化分类爬取器
        
        Args:
            browser_manager: 浏览器管理器实例，如果不提供会创建新的
        """
        self.browser_manager = browser_manager or create_browser_manager()
        self.root_url = Settings.URLS['root']
    
    def _scroll_to_bottom(self, driver):
        """滚动到页面底部，加载所有内容"""
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_pause = Settings.CRAWLER['scroll_pause']
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            last_height = new_height
    
    def _is_valid_link(self, href: str) -> bool:
        """检查链接是否有效"""
        if not href:
            return False
        
        href_lower = href.lower()
        return not any(pattern in href_lower for pattern in self.EXCLUDE_PATTERNS)
    
    def extract_classification_links(self) -> List[Dict[str, str]]:
        """
        提取所有分类链接
        
        Returns:
            分类链接列表，每项包含 name 和 url
        """
        links = []
        
        with self.browser_manager.get_browser() as driver:
            try:
                self.logger.info(f"🌐 打开分类根页面: {self.root_url}")
                driver.get(self.root_url)
                
                # 等待页面加载
                WebDriverWait(driver, Settings.CRAWLER['timeout']).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
                
                # 滚动加载所有内容
                self._scroll_to_bottom(driver)
                
                # 查找所有分类链接
                elements = driver.find_elements(
                    By.CSS_SELECTOR, 
                    "a[href*='traceparts-classification-']"
                )
                
                seen_urls = set()
                for element in elements:
                    href = element.get_attribute('href') or ''
                    
                    if not self._is_valid_link(href) or href in seen_urls:
                        continue
                    
                    seen_urls.add(href)
                    name = element.text.strip() or href.split('/')[-1]
                    
                    links.append({
                        'name': name,
                        'url': href
                    })
                
                self.logger.info(f"🔗 提取到 {len(links)} 个分类链接")
                register_success()
                
            except TimeoutException as e:
                self.logger.error(f"页面加载超时: {e}")
                register_fail('timeout')
                raise
            except Exception as e:
                self.logger.error(f"提取分类链接失败: {e}")
                register_fail('parse')
                raise
        
        return links
    
    def analyse_level(self, url: str) -> int:
        """
        分析URL的层级
        
        Args:
            url: 分类URL
            
        Returns:
            层级数字
        """
        if '%3ATRACEPARTS' in url:
            return 1
        
        if 'CatalogPath=TRACEPARTS%3A' in url:
            code = url.split('CatalogPath=TRACEPARTS%3A')[1].split('&')[0]
            if code.startswith('TP'):
                suffix = code[2:]
                if len(suffix) <= 2:
                    return 2
                return 2 + len(suffix) // 3
        
        # 默认返回第2层
        return 2
    
    def _extract_code(self, url: str) -> str:
        """从URL中提取代码"""
        if 'CatalogPath=TRACEPARTS%3A' in url:
            code = url.split('CatalogPath=TRACEPARTS%3A')[1].split('&')[0]
            return code
        return url.split('/')[-1][:30]
    
    def build_tree(self, links: List[Dict[str, str]]) -> Tuple[Dict, List[Dict]]:
        """
        构建分类树结构
        
        Args:
            links: 分类链接列表
            
        Returns:
            (根节点, 叶节点列表)
        """
        # 为每个链接添加层级信息
        for link in links:
            link['level'] = self.analyse_level(link['url'])
        
        # 按层级和名称排序
        links.sort(key=lambda x: (x['level'], x['name']))
        
        # 创建根节点
        root = {
            'name': 'TraceParts',
            'level': 1,
            'url': self.root_url,
            'code': 'TRACE_ROOT',
            'children': [],
            'is_leaf': False
        }
        
        # 代码映射表
        code_map = {'TRACE_ROOT': root}
        leaves = []
        
        # 构建树结构
        for link in links:
            code = self._extract_code(link['url'])
            
            node = {
                'name': link['name'],
                'url': link['url'],
                'level': link['level'],
                'code': code,
                'children': [],
                'is_leaf': False
            }
            
            code_map[code] = node
            
            # 找到父节点
            if node['level'] == 2:
                parent_code = 'TRACE_ROOT'
            else:
                # 假设代码结构是每3位一层
                parent_code = code[:-3]
            
            parent = code_map.get(parent_code, root)
            parent['children'].append(node)
        
        # 标记叶节点
        def mark_leaves(node):
            if not node.get('children'):
                node['is_leaf'] = True
                leaves.append(node)
            else:
                for child in node['children']:
                    mark_leaves(child)
        
        mark_leaves(root)
        
        self.logger.info(f"🌳 构建分类树完成，共 {len(leaves)} 个叶节点")
        return root, leaves
    
    def crawl_full_tree(self) -> Tuple[Dict, List[Dict]]:
        """
        爬取完整的分类树
        
        Returns:
            (根节点, 叶节点列表)
        """
        try:
            # 提取分类链接
            links = self.extract_classification_links()
            
            if not links:
                self.logger.warning("未能提取到任何分类链接")
                return None, []
            
            # 构建树结构
            root, leaves = self.build_tree(links)
            
            return root, leaves
            
        except Exception as e:
            self.logger.error(f"爬取分类树失败: {e}")
            raise
    
    def get_leaf_nodes(self, root: Dict) -> List[Dict]:
        """
        从树结构中提取所有叶节点
        
        Args:
            root: 根节点
            
        Returns:
            叶节点列表
        """
        leaves = []
        
        def collect_leaves(node):
            if node.get('is_leaf', False):
                leaves.append(node)
            else:
                for child in node.get('children', []):
                    collect_leaves(child)
        
        collect_leaves(root)
        return leaves 