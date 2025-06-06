#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极性能产品链接爬取模块
=====================
消除所有发现的微小开销，达到极致性能
"""

import time
import logging
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class UltimateProductLinksCrawler:
    """终极性能产品链接爬取器 - 消除所有微小开销"""
    
    def __init__(self, log_level: int = logging.INFO):
        """
        初始化终极性能爬取器
        
        Args:
            log_level: 日志级别
        """
        # 预编译所有配置，避免动态读取
        self.TIMEOUT = 60
        self.MAX_NO_CHANGE = 10
        self.MAX_CLICKS = 200
        self.SCROLL_POSITIONS = [0.9, 1.0]  # 预编译抖动位置
        self.MAX_RETRY = 3
        
        # 预编译按钮选择器 (简化到最有效的4个)
        self.BUTTON_SELECTORS = [
            "button.more-results",
            "button.tp-button.more-results",
            "//button[contains(@class, 'more-results')]",
            "//button[contains(text(), 'Show more')]"
        ]
        
        # 简单日志设置 (一次性)
        self.logger = logging.getLogger("ultimate-products")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            self.logger.addHandler(handler)
        self.logger.setLevel(log_level)
        # 防止日志向上传播，避免重复输出
        self.logger.propagate = False
    
    def _create_ultimate_driver(self):
        """创建终极性能驱动 (预编译所有选项)"""
        options = Options()
        # 预编译所有选项，避免动态读取
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(self.TIMEOUT)
        return driver
    
    def _click_show_more_ultimate(self, driver) -> bool:
        """终极优化的按钮点击 (简化到最有效的逻辑)"""
        # 移除5秒等待循环，直接尝试最有效的选择器
        for selector in self.BUTTON_SELECTORS:
            try:
                if selector.startswith('//'):
                    elem = driver.find_element(By.XPATH, selector)
                else:
                    elem = driver.find_element(By.CSS_SELECTOR, selector)
                    
                if elem.is_displayed() and elem.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                    time.sleep(0.3)  # 固定短暂等待
                    driver.execute_script("arguments[0].click();", elem)
                    return True
            except:
                continue
        return False
    
    def _smart_load_ultimate(self, driver):
        """终极性能智能加载 (自动检测产品数量)"""
        self.logger.debug("开始智能加载产品...")
        
        # 初始滚动
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # 预编译所有变量，避免重复查找
        last_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        no_change_count = 0
        click_count = 0
        first_log = True
        
        while True:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
            
            # 首次记录或有显著变化时记录
            if first_log or (current_count - last_count) >= 50:  # 改为50个产品才记录一次
                self.logger.debug(f"当前产品数: {current_count}")
                first_log = False
                
            # 变化检查
            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= self.MAX_NO_CHANGE:
                    self.logger.info(f"📦 成功加载 {current_count} 个产品")
                    break
            else:
                no_change_count = 0
                last_count = current_count
                
            # 简化的按钮点击
            if self._click_show_more_ultimate(driver):
                click_count += 1
                # 将点击日志改为debug级别，避免干扰主要信息
                if click_count % 10 == 0:
                    self.logger.debug(f"已点击 Show More {click_count} 次")
                time.sleep(1.5)
            else:
                # 简单滚动
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                
            # 预编译的抖动滚动
            if no_change_count >= 2:
                for pos in self.SCROLL_POSITIONS:
                    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {pos});")
                    time.sleep(0.3)
                    
            # 预编译的最大点击限制
            if click_count > self.MAX_CLICKS:
                self.logger.warning(f"已点击 {self.MAX_CLICKS} 次，停止加载")
                break
                
        return current_count
    
    def _extract_links_ultimate(self, driver):
        """终极性能链接提取 (预编译JavaScript)"""
        # 预编译JavaScript，避免字符串拼接
        js_code = """
            return Array.from(new Set(
                Array.from(document.querySelectorAll('a[href*="&Product="]'))
                    .filter(a => a.href.includes('/product/'))
                    .map(a => a.href)
            ));
        """
        return driver.execute_script(js_code)
    
    def extract_product_links(self, url: str) -> List[str]:
        """
        提取产品链接 (终极性能版本)
        
        Args:
            url: 页面URL
            
        Returns:
            产品链接列表
        """
        for attempt in range(1, self.MAX_RETRY + 1):
            driver = None
            try:
                if attempt > 1:
                    self.logger.warning(f"重试 {attempt}/{self.MAX_RETRY}: {url}")
                
                # 创建驱动
                driver = self._create_ultimate_driver()
                
                # 直接访问目标页面
                #self.logger.info(f"🌐 打开页面: {url}")  # 显示完整URL
                driver.get(url)
                
                # 等待页面加载完成，但不强制要求有产品链接
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # 等待额外时间让页面内容加载
                time.sleep(3)
                
                # 检查是否有产品链接存在
                product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']")
                if not product_links:
                    self.logger.debug(f"❌ 该分类页面没有产品链接: {url}")
                    return []  # 没有产品，直接返回空列表
                
                # 智能加载所有产品
                final_count = self._smart_load_ultimate(driver)
                
                # 提取所有链接
                self.logger.debug("📦 提取产品链接...")
                all_links = self._extract_links_ultimate(driver)
                
                # 只有在主pipeline中才需要看到这个信息，这里不需要
                return all_links
                
            except Exception as e:
                self.logger.warning(f"尝试 {attempt} 失败: {e}")
                if attempt < self.MAX_RETRY:
                    time.sleep(2)  # 简单重试延迟
                else:
                    self.logger.error("达到最大重试次数，提取失败")
                    return []
            finally:
                if driver:
                    driver.quit()
        
        return []
    
    def extract_batch_product_links(self, urls: List[str]) -> List[List[str]]:
        """
        批量提取产品链接 (终极性能版本)
        
        Args:
            urls: URL列表
            
        Returns:
            每个URL对应的产品链接列表
        """
        results = []
        
        for i, url in enumerate(urls):
            self.logger.info(f"处理第 {i+1}/{len(urls)} 个URL")
            links = self.extract_product_links(url)
            results.append(links)
            
        return results 