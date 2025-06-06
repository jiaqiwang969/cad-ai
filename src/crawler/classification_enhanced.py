#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类树爬取模块
============
使用简单的Selenium方法构建分类树（test-06风格）
产品提取使用高级Playwright策略（test-08风格）
"""

import re
import time
import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue
import random

# Selenium导入
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# 导入配置
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import Settings


class EnhancedClassificationCrawler:
    """分类树爬取器 - 使用简单Selenium方法（test-06风格）"""
    
    # 预编译配置常量
    ROOT_URL = Settings.URLS['root']
    TIMEOUT = Settings.CRAWLER['timeout']
    SCROLL_PAUSE = Settings.CRAWLER['scroll_pause']
    
    # 排除的链接模式
    EXCLUDE_PATTERNS = [
        "sign-in", "sign-up", "login", "register",
        "javascript:", "mailto:", "#", "cookie"
    ]
    
    def __init__(self, log_level: int = logging.INFO, headless: bool = True, debug_mode: bool = False):
        """初始化分类爬取器"""
        self.logger = logging.getLogger("classification-crawler")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            self.logger.addHandler(handler)
        self.logger.setLevel(log_level)
        self.logger.propagate = False
        
        self.headless = headless
        self.debug_mode = debug_mode
        self.driver = None
        
        # 浏览器池用于并行检测
        self.browser_pool = Queue()
        self.pool_lock = threading.Lock()
        self.pool_initialized = False
    
    def _prepare_driver(self) -> webdriver.Chrome:
        """创建简单的Chrome驱动（test-06风格）"""
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium未安装，无法运行分类爬取器！")
        
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(40)
        self.logger.info("✅ 简单浏览器创建完成")
        return self.driver
    
    def _initialize_browser_pool(self, pool_size: int):
        """初始化浏览器池，创建指定数量的浏览器实例"""
        with self.pool_lock:
            if self.pool_initialized:
                return
            
            self.logger.info(f"🏊 初始化浏览器池，创建 {pool_size} 个浏览器实例...")
            
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            for i in range(pool_size):
                try:
                    driver = webdriver.Chrome(options=chrome_options)
                    driver.set_page_load_timeout(40)
                    self.browser_pool.put(driver)
                    self.logger.info(f"  🎉 浏览器池 {i+1}/{pool_size} 创建并加入池中")
                except Exception as e:
                    self.logger.error(f"  ❌ 浏览器 {i+1} 创建失败: {e}")
            
            self.pool_initialized = True
            self.logger.info(f"🚀 浏览器池初始化完成，共 {self.browser_pool.qsize()} 个可用浏览器")
    
    def _get_browser_from_pool(self) -> webdriver.Chrome:
        """从浏览器池获取一个浏览器实例"""
        if self.debug_mode:
            self.logger.info(f"🔄 从浏览器池获取浏览器，当前池大小: {self.browser_pool.qsize()}")
        
        try:
            driver = self.browser_pool.get(timeout=5)  # 缩短超时时间
            # 验证浏览器是否还有效
            try:
                driver.current_url  # 简单测试浏览器是否可用
                if self.debug_mode:
                    self.logger.info("✅ 从池中获取有效浏览器")
                return driver
            except:
                # 浏览器已失效，创建新的
                self.logger.warning("⚠️ 从池中获取的浏览器已失效，创建新的")
                return self._create_pool_browser()
        except Exception as e:
            # 如果池为空或超时，创建一个临时浏览器
            self.logger.warning(f"⚠️ 从浏览器池获取失败: {e}，创建临时浏览器")
            return self._create_pool_browser()
    
    def _create_pool_browser(self) -> webdriver.Chrome:
        """创建池用的浏览器实例"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(40)
        return driver
    
    def _return_browser_to_pool(self, driver: webdriver.Chrome):
        """将浏览器实例返回到池中"""
        if driver:
            try:
                # 清理浏览器状态
                driver.delete_all_cookies()
                self.browser_pool.put(driver)
                if self.debug_mode:
                    self.logger.info(f"🔄 浏览器返回到池中，当前池大小: {self.browser_pool.qsize()}")
            except Exception as e:
                self.logger.warning(f"⚠️ 返回浏览器到池中失败: {e}")
                try:
                    driver.quit()
                except:
                    pass
    
    def _cleanup_browser_pool(self):
        """清理浏览器池，关闭所有浏览器"""
        self.logger.info("🧹 清理浏览器池...")
        closed_count = 0
        while not self.browser_pool.empty():
            try:
                driver = self.browser_pool.get_nowait()
                driver.quit()
                closed_count += 1
            except Exception as e:
                self.logger.warning(f"⚠️ 关闭浏览器时出错: {e}")
        self.logger.info(f"✅ 已关闭 {closed_count} 个浏览器")
    
    def _scroll_full(self, driver: webdriver.Chrome):
        """滚动页面到底部（test-06风格）"""
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        # 回到顶部
        driver.execute_script("window.scrollTo(0,0);")
    
    def _extract_links(self, driver: webdriver.Chrome) -> List[Dict]:
        """提取分类链接（test-06风格）"""
        elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='traceparts-classification-']")
        self.logger.info(f"🔗 共捕获 {len(elements)} 个包含 classification 的链接节点")
        records = []
        seen = set()

        def guess_name_from_href(href: str) -> str:
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
    
    def extract_classification_links_enhanced(self) -> List[Dict[str, str]]:
        """提取分类链接（简单Selenium方法，test-06风格）"""
        try:
            # 创建简单的Chrome驱动
            driver = self._prepare_driver()
            
            self.logger.info(f"🌐 打开分类根页面: {self.ROOT_URL}")
            driver.get(self.ROOT_URL)
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            time.sleep(4)
            
            # 滚动并加载所有内容
            self._scroll_full(driver)
            
            # 提取链接
            records = self._extract_links(driver)
            
            return records
            
        except Exception as e:
            self.logger.error(f"提取分类链接失败: {e}")
            raise
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            self.logger.warning(f"清理资源时出错: {e}")
    
    def analyse_level(self, url: str) -> int:
        """根据 CatalogPath 的 TP 编码推断层级（完全复刻测试文件06）"""
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
    
    def _check_if_real_leaf_node(self, url: str) -> bool:
        """检查URL是否真的是叶节点（包含产品）"""
        if not url:
            return False
            
        try:
            self.logger.info(f"🔍 检查叶节点: {url[:100]}...")
            
            # 使用当前已有的driver实例，如果没有则创建
            if not self.driver:
                self.driver = self._prepare_driver()
            
            # 修改URL以支持更大的PageSize，快速检测
            enhanced_url = self._append_page_size(url, 100)
            self.driver.get(enhanced_url)
            
            # 等待页面加载
            time.sleep(2)  # 减少等待时间
            
            # 获取页面文本内容
            page_text = self.driver.page_source
            
            # === 叶节点检测（遵循 test/08 逻辑） ===
            has_results_keyword = 'results' in page_text.lower()
            has_sort_by = 'sort by' in page_text.lower()

            target_count = self._extract_target_product_count(page_text) if has_results_keyword else 0
            has_positive_count = target_count > 0

            is_leaf = has_results_keyword and has_sort_by and has_positive_count

            # 日志信息
            self.logger.info(
                f"      • results关键字: {has_results_keyword} | Sort by: {has_sort_by} | count: {target_count} -> {'✅叶节点' if is_leaf else '❌非叶节点'}"
            )
            # =====================================
            
            return is_leaf
                
        except Exception as e:
            self.logger.warning(f"⚠️ 叶节点检测失败: {e}")
            return False
    
    def _append_page_size(self, url: str, page_size: int) -> str:
        """为URL添加PageSize参数"""
        if '?' in url:
            return f"{url}&PageSize={page_size}"
        else:
            return f"{url}?PageSize={page_size}"
    
    def verify_leaf_nodes(self, tree_data: Dict, max_workers: int = 16) -> Dict:
        """验证分类树中的潜在叶节点，返回更新后的树"""
        self.logger.info("🧐 开始验证叶节点...")
        
        potential_leaves_to_check = []
        
        def collect_leaves(node):
            if node.get('is_potential_leaf'):
                potential_leaves_to_check.append(node)
            for child in node.get('children', []):
                    collect_leaves(child)
        
        collect_leaves(tree_data)
        
        if not potential_leaves_to_check:
            self.logger.info("🤷 没有找到需要检测的潜在叶节点。")
            return tree_data

        self.logger.info(f"🕵️‍♀️ 将检测 {len(potential_leaves_to_check)} 个潜在叶节点...")
        
        # 使用线程池并行检测
        # Ensure ThreadSafeLogger is used if logging from threads, which it is.
        # Playwright in _check_single_leaf_node is thread-safe as it creates new instances.

        # Limit max_workers to avoid overwhelming system resources, especially with Playwright
        effective_max_workers = min(max_workers, Settings.CRAWLER.get('classification_max_workers', 16))
        
        # Results will be stored by node code to update the tree later
        # However, direct tree modification from threads is not safe.
        # We collect results and then update the main tree sequentially.
        
        # Progress tracking
        processed_count = 0
        lock = threading.Lock()

        # Store results to apply them sequentially later
        results_map = {} # node_code -> (is_leaf_status, product_count_from_check, details_dict)

        def process_node(node, index, total):
            nonlocal processed_count
            node_code = node['code']
            try:
                # _check_single_leaf_node now returns: is_leaf, product_count, details_dict
                is_leaf_status, product_count_from_check, details_dict = self._check_single_leaf_node(node)
                with lock:
                    results_map[node_code] = (is_leaf_status, product_count_from_check, details_dict)
                    processed_count +=1
                    if processed_count % 20 == 0 or processed_count == total:
                         self.logger.info(f"⏳ 叶节点检测进度: {processed_count}/{total} ({(processed_count/total)*100:.1f}%)")
                return # Result stored in map
            except Exception as e:
                self.logger.error(f"Error processing node {node.get('name', 'Unknown')} ({node_code}): {e}", exc_info=self.debug_mode)
                with lock: # Still count as processed for progress
                    results_map[node_code] = (False, 0, {'enhanced_url': node.get('url', ''), 'has_results_keyword': False, 'has_sort_by_keyword': False, 'error': str(e)}) # Store error info
                    processed_count += 1 
                return

        with ThreadPoolExecutor(max_workers=effective_max_workers) as executor:
            futures = []
            for i, node_to_check in enumerate(potential_leaves_to_check):
                futures.append(executor.submit(process_node, node_to_check, i + 1, len(potential_leaves_to_check)))
            
            # Wait for all futures to complete
            for future in as_completed(futures):
                try:
                    future.result() # Ensure exceptions from threads are caught if not handled in process_node
                except Exception as e:
                    self.logger.error(f"Future result error during leaf verification: {e}", exc_info=self.debug_mode)

        self.logger.info(f"🏁 所有 {len(potential_leaves_to_check)} 个潜在叶节点检测完成。开始更新树...")

        # Apply results to the tree (sequentially)
        # This part needs to traverse the tree again to find the nodes by 'code'
        # and update their 'is_leaf' and 'product_count' attributes.
        
        nodes_updated_count = 0
        current_log_index = 0 # For the [index/total] log message

        def update_tree_nodes(node):
            nonlocal nodes_updated_count, current_log_index
            
            node_code = node.get('code')
            if node_code in results_map:
                current_log_index +=1 # Increment for each node that was in results_map
                is_leaf_status, product_count_from_check, details_dict = results_map[node_code]
                
                node['is_leaf'] = is_leaf_status
                node['product_count'] = product_count_from_check
                node['is_verified'] = True # Mark as verified
                nodes_updated_count += 1

                # Construct and log the single INFO message here
                node_name = node.get('name', 'UnknownNode')
                node_level = node.get('level', 0)
                
                enhanced_url = details_dict.get('enhanced_url', node.get('url', 'N/A'))
                has_number_results = details_dict.get('has_number_results_pattern', False)

                result_symbol = '✅' if is_leaf_status else '❌'
                leaf_status_str = '叶' if is_leaf_status else '非叶'
                results_pattern_symbol = '✅' if has_number_results else '❌'
                count_str = str(product_count_from_check) if product_count_from_check > 0 else ('N/A' if not is_leaf_status and product_count_from_check == 0 else '0')


                log_message_main_part = f"结果: [{result_symbol}{leaf_status_str}] (L{node_level}, 数字+results模式: {results_pattern_symbol}) 产品数: {count_str}"
                log_message_url_part = f"测试链接地址: {enhanced_url}"
                
                if 'error' in details_dict:
                     self.logger.error(f"ERROR [{current_log_index}/{len(potential_leaves_to_check)}] {node_name}: Processing error - {details_dict['error']}")
                else:
                    self.logger.info(f"[{current_log_index}/{len(potential_leaves_to_check)}] {node_name}: {log_message_main_part}, {log_message_url_part}")

            # Recursively process children
            for child in node.get('children', []):
                update_tree_nodes(child)

        update_tree_nodes(tree_data)
        self.logger.info(f"✅ 分类树叶节点状态更新完成。共更新 {nodes_updated_count} 个节点。")
        
        return tree_data
    
    def _check_single_leaf_node(self, node: Dict) -> Tuple[bool, int, Dict]:
        """单个叶节点检测（线程安全，独立driver），使用与 test-08 完全一致的 Playwright 逻辑"""
        url = node.get('url')
        node_name = node.get('name', 'UnknownNode')
        
        details_for_log = {
            'enhanced_url': '',
            'has_number_results_pattern': False,
        }

        if not url:
            self.logger.debug(f"Node {node_name} has no URL.")
            return False, 0, details_for_log
        
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
            import time
            import random
            
            # 增强URL - 与 test-08 相同
            enhanced_url = self._append_page_size(url, 500)  # 使用与 test-08 相同的 PageSize=500
            details_for_log['enhanced_url'] = enhanced_url
            self.logger.debug(f"🔍 Playwright检测 [{node_name}]: {enhanced_url}")
            
            with sync_playwright() as p:
                browser = None
                try:
                    browser = p.chromium.launch(
                        headless=Settings.CRAWLER.get('playwright_headless', True),
                        args=[
                            '--no-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-web-security',
                            '--disable-features=VizDisplayCompositor',
                            '--disable-background-timer-throttling',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-renderer-backgrounding'
                        ]
                    )
                    context = browser.new_context(
                        user_agent=Settings.CRAWLER.get('playwright_user_agent', None),
                        java_script_enabled=True,
                        ignore_https_errors=True,
                        bypass_csp=True,  # 绕过内容安全策略
                        extra_http_headers={'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'}
                    )
                    page = context.new_page()
                    
                    # 访问页面并等待网络空闲 - 添加重试机制和更灵活的等待策略
                    max_retries = 2
                    retry_delay = 3
                    
                    for attempt in range(max_retries + 1):
                        try:
                            # 使用更宽松的超时设置和等待策略
                            page.goto(enhanced_url, timeout=45000, wait_until='domcontentloaded')
                            # 尝试等待网络空闲，但设置较短超时，失败则继续
                            try:
                                page.wait_for_load_state("networkidle", timeout=10000)
                            except:
                                self.logger.debug(f"⚠️ [{node_name}] 网络空闲等待超时，继续处理...")
                            
                            time.sleep(2)  # 等待页面稳定
                            break  # 成功加载，退出重试循环
                            
                        except Exception as load_error:
                            if attempt < max_retries:
                                self.logger.warning(f"⚠️ [{node_name}] 第{attempt+1}次加载失败，{retry_delay}秒后重试: {load_error}")
                                time.sleep(retry_delay)
                                continue
                            else:
                                # 最后一次重试失败，抛出异常
                                raise load_error
                    
                    # 检测叶节点 - 与 test-08 完全相同的逻辑（简化为数字+results模式）
                    page_text = page.text_content("body")
                    
                    # 使用正则表达式检测"数字+results"模式
                    # 支持逗号分隔的数字和不间断空格(\u00a0)
                    import re
                    results_pattern = r'\b[\d,]+(?:\s|\u00a0)+results?\b'
                    has_number_results = bool(re.search(results_pattern, page_text, re.IGNORECASE))
                    
                    # 记录检测结果
                    details_for_log['has_number_results_pattern'] = has_number_results
                    
                    self.logger.debug(f"🔍 叶节点检测 [{node_name}]: 数字+results模式={'✅' if has_number_results else '❌'}")
                    
                    # 提取目标产品总数
                    target_count = 0
                    if has_number_results:
                        self.logger.debug(f"✅ 确认这是一个叶节点页面（基于数字+results模式）: {node_name}")
                        target_count = self._extract_target_product_count_test08_style(page_text)
                        
                        # 最终叶节点判断逻辑：与 test-08 保持一致
                        is_leaf = True  # 有数字+results模式就是叶节点
                    else:
                        self.logger.debug(f"⚠️ 这可能不是叶节点页面（未检测到数字+results模式）: {node_name}")
                        is_leaf = False
                    
                    return is_leaf, target_count, details_for_log
                    
                except Exception as pw_error:
                    self.logger.warning(f"⚠️ Playwright页面处理失败 for [{node_name}] ({enhanced_url}): {pw_error}", exc_info=self.debug_mode)
                    details_for_log['error'] = str(pw_error)
                    return False, 0, details_for_log
                finally:
                    if browser:
                        browser.close()
                    
        except Exception as e:
            self.logger.error(f"❌ Playwright检测严重失败 for [{node_name}] ({url}): {e}", exc_info=self.debug_mode)
            details_for_log['error'] = str(e)
            return False, 0, details_for_log
    
    def _check_if_real_leaf_node_batch(self, url: str) -> bool:
        """批量检测模式下的叶节点检测（复用driver）"""
        if not url:
            return False
            
        try:
            # 修改URL以支持更大的PageSize，快速检测
            enhanced_url = self._append_page_size(url, 100)
            self.driver.get(enhanced_url)
            
            # 等待页面加载
            time.sleep(2)
            
            # 获取页面文本内容
            page_text = self.driver.page_source
            
            # 严格检查"数字 + results"模式，排除干扰
            import re
            # 修正的正则：匹配任意数字（可能带逗号分隔）+ 空格 + results
            has_numbered_results = bool(re.search(r'\b\d{1,3}(?:,\d{3})*\s+results?\b|\b\d{4,}\s+results?\b', page_text, re.IGNORECASE))
            
            # 额外检查：排除"0 results"和干扰词
            if has_numbered_results:
                # 排除0结果
                if re.search(r'\b0\s+results?\b', page_text, re.IGNORECASE):
                    has_numbered_results = False
                else:
                    # 确保不是"search results"等干扰词
                    interference_patterns = [
                        r'search\s+\d+\s+results',
                        r'filter\s+\d+\s+results', 
                        r'found\s+\d+\s+results',
                        r'showing\s+\d+\s+results'
                    ]
                    for pattern in interference_patterns:
                        if re.search(pattern, page_text, re.IGNORECASE):
                            # 进一步验证是否真的是产品结果
                            if not (has_product_links or 'Sort by' in page_text):
                                has_numbered_results = False
                                break
            
            # 检查是否有产品链接
            product_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']")
            has_product_links = len(product_links) > 0
            
            # 检查Sort by关键字（辅助判断）
            has_sort_by = 'Sort by' in page_text or 'sort by' in page_text.lower()
            
            # 判断是否为叶节点：必须有数字+results 或 产品链接
            is_leaf = has_numbered_results or has_product_links
            
            if self.debug_mode or is_leaf:  # 只记录叶节点或debug模式
                self.logger.info(f"📊 检测结果: 数字+results={has_numbered_results}, 产品链接={has_product_links}({len(product_links)}个), Sort by={has_sort_by} => {'✅叶节点' if is_leaf else '❌非叶节点'}")
            
            return is_leaf
                
        except Exception as e:
            self.logger.warning(f"⚠️ 页面检测失败: {e}")
            return False
    
    def build_classification_tree(self, records: List[Dict[str, str]]) -> Tuple[Dict, List[Dict]]:
        """构建分类树（修复版）"""
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
        
        # 构建嵌套树（修复版）
        root = {
            'name': 'TraceParts Classification',
            'url': self.ROOT_URL,
            'level': 1,
            'code': 'TRACEPARTS_ROOT',
            'children': []
        }
        code_map = {'TRACEPARTS_ROOT': root}
        
        # 构建树结构 - 修复版
        for rec in enriched:
            node = {
                'name': rec['name'],
                'url': rec['url'],
                'level': rec['level'],
                'code': rec['code'],
                'children': []
            }
            code_map[node['code']] = node
            
            # 确定父code - 使用修复的逻辑
            if node['level'] == 2:
                parent_code = 'TRACEPARTS_ROOT'
            else:
                # 智能的父code计算
                code = node['code']
                if code.startswith('TP') and len(code) > 2:
                    code_num = code[2:]  # 去掉'TP'前缀
                    
                    if len(code_num) <= 2:  # TP01, TP14 等
                        parent_code = 'TRACEPARTS_ROOT'
                    elif len(code_num) == 3:  # TP014 -> 父节点应该是根节点
                        if code_num.isdigit():  # 纯数字如 TP014
                            parent_code = 'TRACEPARTS_ROOT'
                        else:  # TP001 -> TP01
                            parent_code = 'TP' + code_num[:2]
                    elif len(code_num) == 6:  # TP001002 -> TP001
                        parent_code = 'TP' + code_num[:3]
                    elif len(code_num) == 9:  # TP001002003 -> TP001002
                        parent_code = 'TP' + code_num[:6]
                    else:
                        # 回退到原逻辑
                        parent_code = code[:-3]
                else:
                    # 非TP开头的code，使用原逻辑
                    parent_code = code[:-3] if len(code) > 3 else 'TRACEPARTS_ROOT'
            
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
        
        # 简单标记潜在叶节点：先用基本规则标记，后续批量检测
        leaves = []
        
        def mark_potential_leaves(node):
            """递归标记潜在叶节点（基本规则）"""
            # 跳过占位符节点和根节点
            if node['level'] <= 1 or node['name'] == '(placeholder)':
                node['is_leaf'] = False
            else:
                # 优化策略：区分确定叶节点和需要检测的节点
                has_no_children = not node.get('children')
                
                if has_no_children:
                    # 步骤1: 任何没有子节点的节点都是树的最末尾，直接确定为叶节点，无需检测
                    node['is_leaf'] = True
                    node['is_potential_leaf'] = False
                    leaves.append(node)
                    self.logger.info(f"✅ 确定叶节点: {node['name']} (层级: L{node['level']}) - 树末尾节点，无需检测")
                else:
                    # 步骤2: 有子节点的节点需要进一步判断是否为潜在叶节点
                    node['is_leaf'] = False  # 初始标记为非叶节点，等待检测确认
                    
                    # 根据层级判断是否为潜在叶节点（采用之前的检测逻辑）
                    level = node.get('level', 0)
                    if level >= 2:  # L2及以上层级的节点可能是叶节点 (以前是 L4)
                        node['is_potential_leaf'] = True
                        leaves.append(node)  # 加入待检测列表
                        self.logger.info(f"🔍 潜在叶节点: {node['name']} (层级: L{level}) - 有子节点但需检测")
                    else:
                        node['is_potential_leaf'] = False
                        self.logger.debug(f"❌ 非叶节点: {node['name']} (层级: L{level}) - 层级过低且有子节点")
            
            # 处理子节点
            if node.get('children'):
                for child in node['children']:
                    mark_potential_leaves(child)
        
        mark_potential_leaves(root)
        
        # 更新根节点统计信息
        root['total_nodes'] = len(enriched) + 1
        root['total_leaves'] = len(leaves)
        
        self.logger.info(f"🌳 构建分类树完成，共 {len(leaves)} 个叶节点")
        
        return root, leaves
    
    def crawl_full_tree_enhanced(self) -> Tuple[Dict, List[Dict]]:
        """爬取完整分类树（增强版）"""
        try:
            # 提取链接
            records = self.extract_classification_links_enhanced()
            
            if not records:
                self.logger.warning("未能提取到任何分类链接")
                return None, []
            
            # 构建树
            root, potential_leaves = self.build_classification_tree(records)
            
            # 批量检测叶节点
            self.logger.info("🔍 开始批量检测真实叶节点...")
            verified_root = self.verify_leaf_nodes(root)
            
            # 收集所有叶节点（确定的+检测确认的）
            all_leaves = []
            def collect_all_leaves(node):
                if node.get('is_leaf') == True:
                    all_leaves.append(node)
                if node.get('children'):
                    for child in node['children']:
                        collect_all_leaves(child)
            
            collect_all_leaves(verified_root)
            
            self.logger.info(f"✅ 叶节点验证完成: 总共 {len(all_leaves)} 个真实叶节点")
            
            return verified_root, all_leaves
            
        except Exception as e:
            self.logger.error(f"爬取分类树失败: {e}")
            return None, []

    # ----------------- 新增: 提取产品数量 -----------------
    def _extract_target_product_count_test08_style(self, page_text: str) -> int:
        """从页面提取目标产品总数 - 与 test-08 完全一致的逻辑"""
        try:
            # 常见的产品数量显示模式，支持逗号分隔符
            count_patterns = [
                r"([\d,]+)\s*results?",
                r"([\d,]+)\s*products?", 
                r"([\d,]+)\s*items?",
                r"showing\s*[\d,]+\s*[-–]\s*[\d,]+\s*of\s*([\d,]+)",
                r"([\d,]+)\s*total",
                r"found\s*([\d,]+)"
            ]
            
            # 获取页面全部文本内容并转为小写
            page_text_lower = page_text.lower()
            
            self.logger.debug(f"🔍 搜索产品数量模式...")
            
            # 尝试匹配各种模式
            for pattern in count_patterns:
                if self.debug_mode:
                    self.logger.debug(f"  📄 尝试模式: {pattern}")
                matches = re.findall(pattern, page_text_lower, re.IGNORECASE)
                if matches:
                    if self.debug_mode:
                        self.logger.debug(f"    🎉 模式 {pattern} 匹配到: {matches}")
                    for match_item in matches:
                        try:
                            # re.findall 返回的是元组列表，即使只有一个捕获组
                            # 如果是元组，取第一个元素；否则，直接使用
                            actual_match_str = match_item if isinstance(match_item, str) else match_item[0]
                            
                            # 移除逗号后转换为整数
                            count_str = actual_match_str.replace(',', '')
                            if not count_str.isdigit(): # 确保是纯数字
                                self.logger.warning(f"      ⚠️ 非数字内容: '{count_str}' (来自: '{actual_match_str}')")
                                continue
                            count = int(count_str)
                            
                            # 更新产品数量范围的下限为1，因为我们关心的是>0
                            if 1 <= count <= 50000:  # 合理的产品数量范围
                                self.logger.debug(f"🎯 发现目标产品总数: {count} (来自模式: '{pattern}', 原文: '{actual_match_str}')")
                                return count
                            else:
                                if self.debug_mode:
                                    self.logger.debug(f"      🔶 数量 {count} 不在有效范围 [1, 50000] (来自: '{actual_match_str}')")
                        except (ValueError, IndexError) as e_inner:
                            self.logger.warning(f"      ⚠️ 处理匹配项 '{match_item}' 时出错: {e_inner}")
                            continue
                else:
                    if self.debug_mode:
                        self.logger.debug(f"    ❌ 模式 {pattern} 未匹配到任何内容")
            
            self.logger.debug("⚠️ 未能提取到目标产品总数")
            return 0
            
        except Exception as e:
            self.logger.warning(f"⚠️ 提取目标产品总数失败: {e}")
            return 0

    def _extract_target_product_count(self, page_text_lower: str) -> int:
        """从页面提取目标产品总数 - 严格对齐 test/08-test_leaf_product_links.py"""
        try:
            # 常见的产品数量显示模式，支持逗号分隔符 (from test/08)
            count_patterns = [
                r"([\d,]+)\s*results?",
                r"([\d,]+)\s*products?", 
                r"([\d,]+)\s*items?",
                r"showing\s*[\d,]+\s*[-–]\s*[\d,]+\s*of\s*([\d,]+)",
                r"([\d,]+)\s*total",
                r"found\s*([\d,]+)"
            ]
            
            self.logger.debug(f"🔍 [ClassEnhanced] 搜索产品数量模式...") 
            
            for pattern in count_patterns:
                if self.debug_mode: 
                    self.logger.debug(f"  📄 [ClassEnhanced] 尝试模式: {pattern}")
                
                matches = re.findall(pattern, page_text_lower, re.IGNORECASE)

                if matches:
                    if self.debug_mode: 
                        self.logger.debug(f"    🎉 [ClassEnhanced] 模式 {pattern} 匹配到: {matches}")
                    for match_item in matches:
                        try:
                            # 对齐 test-08 的简单逻辑：如果是元组，取第一个元素；否则，直接使用
                            actual_match_str = match_item if isinstance(match_item, str) else match_item[0]
                            
                            # 移除逗号后转换为整数
                            count_str = actual_match_str.replace(',', '')
                            if not count_str.isdigit(): # 确保是纯数字
                                if self.debug_mode:
                                    self.logger.debug(f"      ⚠️ [ClassEnhanced] 非数字内容: '{count_str}' (来自: '{actual_match_str}')")
                                continue
                            count = int(count_str)
                            
                            # 合理的产品数量范围 (1 <= count <= 50000)
                            if 1 <= count <= 50000:  
                                self.logger.debug(f"🎯 [ClassEnhanced] 发现目标产品总数: {count} (来自模式: '{pattern}', 原文: '{actual_match_str}')")
                                return count
                            else:
                                if self.debug_mode: 
                                    self.logger.debug(f"      🔶 [ClassEnhanced] 数量 {count} 不在有效范围 [1, 50000] (来自: '{actual_match_str}')")
                        except (ValueError, IndexError) as e_inner:
                            if self.debug_mode: 
                                self.logger.debug(f"      ⚠️ [ClassEnhanced] 处理匹配项 '{match_item}' 时出错: {e_inner}")
                            continue
                else:
                    if self.debug_mode: 
                        self.logger.debug(f"    ❌ [ClassEnhanced] 模式 {pattern} 未匹配到任何内容")
            
            self.logger.debug("⚠️ [ClassEnhanced] 未能提取到目标产品总数")
            return 0
            
        except Exception as e:
            self.logger.warning(f"⚠️ [ClassEnhanced] 提取目标产品总数失败: {e}", exc_info=self.debug_mode)
            return 0

    def get_classification_tree(self, force_refresh: bool = False, retry_failed: bool = False) -> Dict:
        """
        Orchestrates the fetching or generation of the full, verified classification tree.
        This method is called by CacheManager. Caching itself is handled by CacheManager.
        This method focuses on the crawling and verification steps.
        """
        self.logger.info(f"🚀 EnhancedClassificationCrawler:get_classification_tree called (force_refresh={force_refresh}, retry_failed={retry_failed})")

        # Step 1: Crawl the basic tree structure.
        # crawl_full_tree_enhanced returns a tuple (tree_data, all_leaf_nodes_from_crawl)
        self.logger.info("🌳 Building initial classification tree structure...")
        # Note: force_refresh and retry_failed are not directly used by crawl_full_tree_enhanced
        # as it always rebuilds from scratch. CacheManager handles whether to call this.
        tree_data, _ = self.crawl_full_tree_enhanced()
        self.logger.info("🌳 Initial classification tree structure built.")

        # Step 2: Verify the leaf nodes in the tree.
        # verify_leaf_nodes takes the tree_data and max_workers.
        self.logger.info("🧐 Verifying leaf nodes in the tree...")
        
        # Get max_workers from settings, similar to how it's done elsewhere.
        # Ensure Settings is accessible here. If not, a default or passed param is needed.
        # Assuming Settings class is available (it's used above for playwright_headless etc.)
        max_workers_for_verification = Settings.CRAWLER.get('classification_workers', 16)
        
        verified_tree_data = self.verify_leaf_nodes(tree_data, max_workers=max_workers_for_verification)
        self.logger.info("🧐 Leaf node verification complete.")
        
        return verified_tree_data