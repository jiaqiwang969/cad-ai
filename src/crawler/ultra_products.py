#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超高性能产品链接爬取模块
=====================
完全模仿 test_ultra_fast.py 的逻辑，但封装成可重用的类
专注性能，去除所有不必要的开销
"""

import time
import logging
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class UltraProductLinksCrawler:
    """超高性能产品链接爬取器"""
    
    def __init__(self, log_level: int = logging.INFO):
        """
        初始化超高性能爬取器
        
        Args:
            log_level: 日志级别
        """
        # 简单的日志设置
        self.logger = logging.getLogger("ultra-products")
        self.logger.setLevel(log_level)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _create_ultra_fast_driver(self):
        """创建超高性能驱动 (完全模仿test_5099_improved.py)"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        # 固定User-Agent，利用缓存
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(60)
        return driver
    
    def _smart_load_all_products(self, driver, target_count=5099):
        """超高性能智能加载 (完全复刻test_5099_improved.py)"""
        self.logger.info("开始智能加载产品...")
        
        # 1. 初始滚动触发第一次加载
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # 2. 记录产品数变化
        last_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        no_change_count = 0
        click_count = 0
        max_no_change = 10
        
        while True:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
            self.logger.info(f"当前产品数: {current_count}/{target_count} ({current_count/target_count*100:.1f}%)")
            
            # 检查是否达到目标
            if current_count >= target_count:
                self.logger.info(f"✅ 达到目标！获取了全部 {current_count} 个产品")
                break
                
            # 检查是否有变化
            if current_count == last_count:
                no_change_count += 1
                current_max_no_change = max_no_change * 2 if current_count >= target_count * 0.95 else max_no_change
                if no_change_count >= current_max_no_change:
                    self.logger.warning(f"连续 {current_max_no_change} 次没有新产品，可能已达到限制（当前: {current_count}/{target_count}）")
                    break
            else:
                no_change_count = 0
                last_count = current_count
                
            # 策略1：尝试点击"Show More"按钮 (完全复刻原版逻辑)
            try:
                button_selectors = [
                    "button.more-results",
                    "button.tp-button.more-results",
                    "//button[contains(@class, 'more-results')]",
                    "//button[contains(text(), 'Show more results')]",
                    "//button[contains(text(), 'SHOW MORE RESULTS')]",
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show more')]"
                ]
                
                button_found = False
                for selector in button_selectors:
                    try:
                        if selector.startswith('//'):
                            button = driver.find_element(By.XPATH, selector)
                        else:
                            button = driver.find_element(By.CSS_SELECTOR, selector)
                            
                        if button.is_displayed() and button.is_enabled():
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", button)
                            click_count += 1
                            self.logger.info(f"✓ 第 {click_count} 次点击 Show More")
                            button_found = True
                            time.sleep(1.5)
                            break
                    except:
                        continue
                        
                if not button_found:
                    self.logger.debug("未找到Show More按钮，尝试滚动...")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"点击按钮时出错: {e}")
                
            # 策略2：抖动滚动
            if no_change_count >= 2:
                positions = [0.9, 1.0]
                for pos in positions:
                    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {pos});")
                    time.sleep(0.3)
                    
            # 避免无限循环
            if click_count > 200:
                self.logger.warning(f"已点击 {click_count} 次，停止加载")
                break
                
        return current_count
    
    def _extract_all_product_links(self, driver):
        """超高性能链接提取 (完全复刻test_5099_improved.py)"""
        links = driver.execute_script("""
            return Array.from(new Set(
                Array.from(document.querySelectorAll('a[href*="&Product="]'))
                    .filter(a => a.href.includes('/product/'))
                    .map(a => a.href)
            ));
        """)
        return links
    
    def extract_product_links(self, url: str, target_count: int = 5099) -> List[str]:
        """
        提取产品链接 (超高性能版本)
        
        Args:
            url: 页面URL
            target_count: 目标产品数
            
        Returns:
            产品链接列表
        """
        driver = None
        
        try:
            # 创建驱动
            driver = self._create_ultra_fast_driver()
            
            # 直接访问目标页面 (不像生产环境先访问base页面)
            self.logger.info("🌐 打开页面...")
            driver.get(url)
            
            # 等待初始加载
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']"))
            )
            
            # 智能加载所有产品
            final_count = self._smart_load_all_products(driver, target_count)
            
            # 提取所有链接
            self.logger.info("📦 提取产品链接...")
            all_links = self._extract_all_product_links(driver)
            
            self.logger.info(f"从 {url} 提取到 {len(all_links)} 个产品链接")
            return all_links
            
        except Exception as e:
            self.logger.error(f"提取产品链接失败: {e}")
            return []
            
        finally:
            if driver:
                driver.quit()
    
    def extract_batch_product_links(self, urls: List[str], target_count: int = 5099) -> List[List[str]]:
        """
        批量提取产品链接 (超高性能版本)
        
        Args:
            urls: URL列表
            target_count: 每个页面的目标产品数
            
        Returns:
            每个URL对应的产品链接列表
        """
        results = []
        
        for i, url in enumerate(urls):
            self.logger.info(f"处理第 {i+1}/{len(urls)} 个URL: {url}")
            links = self.extract_product_links(url, target_count)
            results.append(links)
            
        return results 