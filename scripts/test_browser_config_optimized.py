#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器配置优化测试
================
对比不同浏览器配置的性能差异
"""

import sys
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("browser-config-test")


def create_fast_driver():
    """创建快速版驱动 (模仿test_5099_improved.py)"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    # 固定User-Agent，利用缓存
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)  # 60秒
    return driver


def create_production_driver():
    """创建生产版驱动 (模仿browser_manager.py)"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # 反检测选项 (增加开销)
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # 随机User-Agent (破坏缓存)
    import random
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    user_agent = agents[random.randint(0, len(agents)-1)]
    options.add_argument(f'--user-agent={user_agent}')
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(90)  # 90秒
    
    # 反检测脚本 (增加开销)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.navigator.chrome = {
                runtime: {}
            };
        '''
    })
    
    return driver


def test_page_load_performance(driver_type):
    """测试页面加载性能"""
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    
    LOG.info(f"测试 {driver_type} 配置...")
    
    if driver_type == "fast":
        driver = create_fast_driver()
    else:
        driver = create_production_driver()
    
    start_time = time.time()
    
    try:
        # 仅测试页面加载时间
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='&Product=']"))
        )
        
        load_time = time.time() - start_time
        
        # 获取初始产品数
        initial_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        
        LOG.info(f"  页面加载时间: {load_time:.2f} 秒")
        LOG.info(f"  初始产品数: {initial_count}")
        
        return load_time, initial_count
        
    except Exception as e:
        LOG.error(f"  加载失败: {e}")
        return None, 0
        
    finally:
        # 生产环境的清理操作
        if driver_type == "production":
            try:
                driver.delete_all_cookies()
                driver.execute_script("window.localStorage.clear();")
                driver.execute_script("window.sessionStorage.clear();")
            except:
                pass
        driver.quit()


def main():
    print("🎯 浏览器配置性能对比测试")
    print("=" * 80)
    
    results = {}
    
    for config_type in ["fast", "production"]:
        print(f"\n测试配置: {config_type.upper()}")
        print("-" * 40)
        
        load_time, count = test_page_load_performance(config_type)
        results[config_type] = (load_time, count)
    
    print("\n" + "=" * 80)
    print("📊 性能对比结果:")
    
    fast_time, fast_count = results.get("fast", (None, 0))
    prod_time, prod_count = results.get("production", (None, 0))
    
    if fast_time and prod_time:
        speedup = prod_time / fast_time
        print(f"  快速配置: {fast_time:.2f}秒, {fast_count}个产品")
        print(f"  生产配置: {prod_time:.2f}秒, {prod_count}个产品") 
        print(f"  性能差异: 生产配置慢 {speedup:.1f}x")
        
        print(f"\n🔍 主要性能瓶颈:")
        print(f"  1. 页面加载超时: 90秒 vs 60秒")
        print(f"  2. 随机User-Agent破坏缓存")
        print(f"  3. 反检测代码开销")
        print(f"  4. 浏览器清理操作")


if __name__ == "__main__":
    main() 