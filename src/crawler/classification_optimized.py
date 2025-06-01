#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版分类树爬取模块
==================
完全复刻测试文件06的逻辑
"""

import re
import time
import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class OptimizedClassificationCrawler:
    """优化版分类树爬取器"""
    
    # 预编译配置常量
    ROOT_URL = 'https://www.traceparts.cn/en/search/traceparts-classification?CatalogPath=TRACEPARTS%3ATRACEPARTS'
    TIMEOUT = 40
    SCROLL_PAUSE = 1.5
    
    # 排除的链接模式
    EXCLUDE_PATTERNS = [
        "sign-in", "sign-up", "login", "register",
        "javascript:", "mailto:", "#"
    ]
    
    def __init__(self, log_level: int = logging.INFO):
        """初始化优化版分类爬取器"""
        # 简单日志设置 (一次性)
        self.logger = logging.getLogger("opt-classification")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            self.logger.addHandler(handler)
        self.logger.setLevel(log_level)
        # 防止日志向上传播，避免重复输出
        self.logger.propagate = False
    
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
    
    def _scroll_to_bottom(self, driver):
        """滚动到页面底部，加载所有内容"""
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.SCROLL_PAUSE)
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            last_height = new_height
        
        # 回到顶部
        driver.execute_script("window.scrollTo(0,0);")
    
    def extract_classification_links(self) -> List[Dict[str, str]]:
        """提取分类链接（完全复刻测试文件06）"""
        driver = None
        
        try:
            driver = self._create_optimized_driver()
            self.logger.info(f"🌐 打开分类根页面: {self.ROOT_URL}")
            driver.get(self.ROOT_URL)
            
            # 等待页面加载
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            time.sleep(4)  # 额外等待
            
            # 滚动加载所有内容
            self._scroll_to_bottom(driver)
            
            # 查找所有分类链接
            elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='traceparts-classification-']")
            self.logger.info(f"🔗 共捕获 {len(elements)} 个包含 classification 的链接节点")
            
            records = []
            seen = set()
            
            def guess_name_from_href(href: str) -> str:
                """从URL推断名称"""
                try:
                    if 'traceparts-classification-' in href:
                        tail = href.split('traceparts-classification-')[1]
                        path_part = tail.split('?')[0].strip('-')
                        if path_part:
                            # 拿最后一个段落作为名称
                            last_seg = path_part.split('-')[-1]
                            return last_seg.replace('-', ' ').replace('_', ' ').title()
                except Exception:
                    pass
                return "Unnamed"
            
            for el in elements:
                href = el.get_attribute('href') or ""
                # 可见文本
                raw_text = el.text.strip()
                if not href or any(pat in href.lower() for pat in self.EXCLUDE_PATTERNS):
                    continue
                # 去重
                if href in seen:
                    continue
                seen.add(href)
                
                name = raw_text
                # 如果可见文本为空，尝试其他属性
                if not name:
                    alt_sources = [
                        el.get_attribute('title'),
                        el.get_attribute('aria-label'),
                        el.get_attribute('data-original-title'),
                        el.get_attribute('innerText'),
                        el.get_attribute('textContent')
                    ]
                    for src in alt_sources:
                        if src and src.strip():
                            name = src.strip()
                            break
                # 仍为空，解析 innerHTML 拿子元素文本
                if not name:
                    inner_html = el.get_attribute('innerHTML') or ""
                    soup = BeautifulSoup(inner_html, 'html.parser')
                    txt = soup.get_text(" ", strip=True)
                    if txt:
                        name = txt
                # 仍为空，尝试从 href 推断
                if not name:
                    name = guess_name_from_href(href)
                
                records.append({"name": name, "url": href})
            
            self.logger.info(f"✅ 过滤后剩余 {len(records)} 条唯一分类链接，其中已填充名称")
            return records
            
        except TimeoutException as e:
            self.logger.error(f"页面加载超时: {e}")
            raise
        except Exception as e:
            self.logger.error(f"提取分类链接失败: {e}")
            raise
        finally:
            if driver:
                driver.quit()
    
    def analyse_level(self, url: str) -> int:
        """根据 CatalogPath 的 TP 编码推断层级（完全复刻测试文件06）
        TP##                           -> L2 (主类目)
        TP##XXX                        -> L3 (1 组 3 位)
        TP##XXXYYY                     -> L4 (2 组)
        依此类推；若无符合规则，退回到基于 '-' 计数法。
        """
        if "%3ATRACEPARTS" in url:
            return 1  # 根分类页面
        
        level_by_dash = None
        # 备用：'-' 计数
        try:
            tail = url.split('traceparts-classification-')[1]
            path_part = tail.split('?')[0].strip('-')
            if path_part:
                level_by_dash = len(path_part.split('-')) + 1  # L2 起
        except Exception:
            pass
        
        # CatalogPath 推断
        cat_path_part = None
        if "CatalogPath=TRACEPARTS%3A" in url:
            cat_path_part = url.split("CatalogPath=TRACEPARTS%3A")[1].split('&')[0]
        if cat_path_part and cat_path_part.startswith("TP"):
            code = cat_path_part[2:]
            if len(code) <= 2:  # TP01..TP14 等
                return 2
            # 剩余每 3 位一个深度
            depth_groups = len(code) // 3
            return 2 + depth_groups
        
        return level_by_dash if level_by_dash else 2
    
    def _extract_code(self, url: str) -> str:
        """从URL中提取代码"""
        if 'CatalogPath=TRACEPARTS%3A' in url:
            code = url.split('CatalogPath=TRACEPARTS%3A')[1].split('&')[0]
            return code
        return url.split('/')[-1][:30]
    
    def build_classification_tree(self, records: List[Dict[str, str]]) -> Tuple[Dict, List[Dict]]:
        """构建分类树（复刻测试文件07的逻辑）"""
        self.logger.info("🌳 开始构建分类树...")
        
        # 为每条记录添加层级和code
        enriched = []
        for rec in records:
            level = self.analyse_level(rec['url'])
            code = self._extract_code(rec['url'])
            enriched.append({
                'name': rec['name'],
                'url': rec['url'],
                'level': level,
                'code': code
            })
        
        # 按层级排序
        enriched.sort(key=lambda x: (x['level'], x['name']))
        
        # 统计层级
        stats = defaultdict(int)
        for item in enriched:
            stats[item['level']] += 1
        self.logger.info("📊 层级统计:" + ", ".join([f"L{lv}:{cnt}" for lv,cnt in sorted(stats.items())]))
        
        # 构建嵌套树（按照测试文件07的逻辑）
        root = {
            'name': 'TraceParts Classification',
            'url': self.ROOT_URL,
            'level': 1,
            'code': 'TRACEPARTS_ROOT',
            'children': []
        }
        code_map = {'TRACEPARTS_ROOT': root}
        
        # 构建树结构
        for rec in enriched:
            node = {
                'name': rec['name'],
                'url': rec['url'],
                'level': rec['level'],
                'code': rec['code'],
                'children': []
            }
            code_map[node['code']] = node
            
            # 确定父code
            if node['level'] == 2:
                parent_code = 'TRACEPARTS_ROOT'
            else:
                parent_code = node['code'][:-3]  # 每3位上溯一级
            
            parent = code_map.get(parent_code)
            if not parent:
                # 创建占位父节点
                parent = code_map.setdefault(parent_code, {
                    'name': '(placeholder)',
                    'url': '',
                    'level': node['level'] - 1,
                    'code': parent_code,
                    'children': []
                })
            parent['children'].append(node)
        
        # 递归标注叶节点
        leaves = []
        
        def mark(node):
            if node.get('children'):
                node['is_leaf'] = False
                for ch in node['children']:
                    mark(ch)
            else:
                node['is_leaf'] = True
                # 不包含根节点和占位节点
                if node['level'] > 1 and node['name'] != '(placeholder)':
                    leaves.append(node)
        
        mark(root)
        
        # 更新根节点统计信息
        root['total_nodes'] = len(enriched) + 1
        root['total_leaves'] = len(leaves)
        
        self.logger.info(f"🌳 构建分类树完成，共 {len(leaves)} 个叶节点")
        
        return root, leaves
    
    def crawl_full_tree(self) -> Tuple[Dict, List[Dict]]:
        """爬取完整分类树"""
        try:
            # 提取链接
            records = self.extract_classification_links()
            
            if not records:
                self.logger.warning("未能提取到任何分类链接")
                return None, []
            
            # 构建树
            root, leaves = self.build_classification_tree(records)
            
            return root, leaves
            
        except Exception as e:
            self.logger.error(f"爬取分类树失败: {e}")
            return None, [] 