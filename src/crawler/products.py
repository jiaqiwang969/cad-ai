#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
产品链接爬取模块
===============
负责从叶节点页面提取产品链接
"""

import time
import os
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from config.settings import Settings
from config.logging_config import LoggerMixin
from src.utils.browser_manager import create_browser_manager
from src.utils.net_guard import register_success, register_fail


class ProductLinksCrawler(LoggerMixin):
    """产品链接爬取器"""
    
    def __init__(self, browser_manager=None):
        """
        初始化产品链接爬取器
        
        Args:
            browser_manager: 浏览器管理器实例
        """
        self.browser_manager = browser_manager or create_browser_manager()
        self.max_retry = Settings.RETRY_STRATEGIES['timeout_error']['max_retry']
    
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
    
    def _inject_session_cookies(self, driver):
        """如果本地保存了 session_cookies.json，则注入到当前 driver"""
        session_file = Settings.AUTH['session_file']
        if not session_file or not os.path.exists(session_file):
            return
        try:
            import json, pathlib
            with open(session_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            for c in cookies:
                # Selenium cookie 字段必须符合规范
                cookie = {
                    'name': c.get('name'),
                    'value': c.get('value'),
                    'domain': c.get('domain', '.traceparts.cn'),
                    'path': c.get('path', '/'),
                    'expiry': c.get('expiry') if c.get('expiry') else None,
                    'secure': c.get('secure', False),
                    'httpOnly': c.get('httpOnly', False)
                }
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    continue
            self.logger.debug("已注入登录 cookies")
        except Exception as e:
            self.logger.warning(f"注入 cookies 失败: {e}")

    def _dismiss_cookie_banner(self, driver):
        """自动关闭 TraceParts 页面的 cookie banner"""
        try:
            banner_btn = driver.find_element(By.CSS_SELECTOR, "button#onetrust-accept-btn-handler")
            if banner_btn.is_displayed():
                banner_btn.click()
                time.sleep(0.5)
                self.logger.debug("已关闭 cookie banner")
        except Exception:
            pass

    def _click_show_more(self, driver) -> bool:
        """尝试点击"Show More"按钮，返回是否点击成功"""
        selectors = [
            "button#load-more-results",
            "button.more-results",
            "button.tp-button.more-results",
            "button.load-more-results",
            "a.more-results",
            "div.more-results",
            "*[class*='more-results']",
            "//button[contains(@class,'more-results')]",
            "//button[contains(text(),'Load more')]",
            "//button[contains(text(),'Show more')]",
            "//button[contains(text(),'更多')]",
            "//button[contains(text(),'加载更多')]",
            "//a[contains(@class,'more-results')]",
        ]
        # 等待按钮出现最多 5 秒
        end_time = time.time() + 5
        while time.time() < end_time:
            for sel in selectors:
                try:
                    elem = driver.find_element(By.XPATH, sel) if sel.startswith('//') else driver.find_element(By.CSS_SELECTOR, sel)
                    if elem.is_displayed() and elem.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", elem)
                        return True
                except Exception:
                    continue
            time.sleep(0.5)
        return False
    
    def _load_all_results(self, driver):
        """加载所有产品（完全复刻 test_5099_improved.py 算法 + 抖动滚动）"""
        self.logger.debug("开始智能加载产品 …")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        last_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        no_change_count = 0
        click_count = 0
        max_no_change = 10
        jitter_positions = [0.9, 1.0]
        while True:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
            # 只在产品数变化时记录日志，避免DEBUG级别的性能影响
            if current_count != last_count:
                self.logger.info(f"当前产品数: {current_count}")
            if current_count == last_count:
                no_change_count += 1
                current_max = max_no_change * 2 if current_count >= 1000 else max_no_change
                if no_change_count >= current_max:
                    self.logger.info(f"连续 {current_max} 次没有新产品，停止加载（最终: {current_count}）")
                    break
            else:
                no_change_count = 0
                last_count = current_count
            if self._click_show_more(driver):
                click_count += 1
                # 降低点击日志频率，避免DEBUG性能影响
                if click_count % 10 == 0:  # 每10次点击记录一次
                    self.logger.info(f"已点击 Show More {click_count} 次")
                time.sleep(1.5)
            else:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            if no_change_count >= 2:
                for pos in jitter_positions:
                    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{pos});")
                    time.sleep(0.3)
            if click_count > 220:
                self.logger.warning("点击次数过多，强制停止")
                break
    
    def _extract_product_links_once(self, leaf_url: str) -> List[str]:
        """
        单次尝试提取产品链接
        
        Args:
            leaf_url: 叶节点URL
            
        Returns:
            产品链接列表
        """
        links = []
        
        with self.browser_manager.get_browser() as driver:
            try:
                self.logger.debug(f"访问叶节点页面: {leaf_url}")
                # 优化: 直接访问目标页面，减少页面加载开销
                # 注释掉双重页面加载以提升性能
                # driver.get(Settings.URLS['base'])
                # self._inject_session_cookies(driver)
                driver.get(leaf_url)
                
                # 等待页面出现至少一个产品链接元素
                WebDriverWait(driver, Settings.CRAWLER['timeout']).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']"))
                )
                self.logger.info("页面基础元素已出现，开始滚动加载 …")
                time.sleep(1)  # 再给页面 1 秒缓冲
                
                # 加载所有结果
                self._load_all_results(driver)
                
                # 使用JavaScript一次性提取所有产品链接
                js_extract = """
                return Array.from(new Set(
                    Array.from(document.querySelectorAll('a[href*="&Product="]'))
                        .filter(a => {
                            const href = a.href;
                            return href.includes('&Product=') && 
                                   href.includes('/product/');
                        })
                        .map(a => a.href)
                ));
                """
                
                links = driver.execute_script(js_extract)
                
                self.logger.info(f"从 {leaf_url} 提取到 {len(links)} 个产品链接")
                # 优化: 注释掉网络监控以提升性能
                # register_success()
                
            except TimeoutException as e:
                self.logger.warning(f"页面加载超时: {leaf_url}")
                register_fail('timeout')
                raise
            except WebDriverException as e:
                self.logger.warning(f"浏览器异常: {e}")
                register_fail('browser')
                raise
            except Exception as e:
                self.logger.error(f"提取产品链接失败: {e}")
                register_fail('parse')
                raise
        
        return links
    
    def extract_product_links(self, leaf_url: str) -> List[str]:
        """
        提取产品链接（带重试）
        
        Args:
            leaf_url: 叶节点URL
            
        Returns:
            产品链接列表
        """
        retry_strategy = Settings.get_retry_strategy('timeout_error')
        max_retry = retry_strategy['max_retry']
        
        for attempt in range(1, max_retry + 1):
            try:
                return self._extract_product_links_once(leaf_url)
                
            except (TimeoutException, WebDriverException) as e:
                if attempt < max_retry:
                    delay = retry_strategy['delay'](attempt)
                    self.logger.warning(
                        f"尝试 {attempt}/{max_retry} 失败，{delay}秒后重试: {leaf_url}"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"达到最大重试次数，放弃: {leaf_url}")
                    return []
            except Exception as e:
                self.logger.error(f"意外错误: {e}")
                return []
        
        return []
    
    def extract_batch_product_links(self, 
                                  leaf_nodes: List[Dict], 
                                  max_workers: int = None) -> Dict[str, List[str]]:
        """
        批量提取产品链接
        
        Args:
            leaf_nodes: 叶节点列表
            max_workers: 最大并发数
            
        Returns:
            {叶节点code: 产品链接列表}
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        max_workers = max_workers or Settings.CRAWLER['max_workers']
        results = {}
        
        self.logger.info(f"开始批量提取 {len(leaf_nodes)} 个叶节点的产品链接")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_node = {
                executor.submit(self.extract_product_links, node['url']): node
                for node in leaf_nodes
            }
            
            # 收集结果
            for future in as_completed(future_to_node):
                node = future_to_node[future]
                try:
                    links = future.result()
                    results[node['code']] = links
                    self.logger.info(
                        f"✅ 叶节点 {node['code']} ({node['name']}) "
                        f"产品数: {len(links)}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"❌ 叶节点 {node['code']} ({node['name']}) "
                        f"失败: {e}"
                    )
                    results[node['code']] = []
        
        # 统计
        total_products = sum(len(links) for links in results.values())
        success_nodes = sum(1 for links in results.values() if links)
        
        self.logger.info(
            f"批量提取完成: {success_nodes}/{len(leaf_nodes)} 个叶节点成功, "
            f"共 {total_products} 个产品链接"
        )
        
        return results 