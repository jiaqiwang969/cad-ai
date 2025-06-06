#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试实时规格提取功能 - 优化版
应用性能优化技巧，看看能提升多少速度
"""

import sys
import logging
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# 全局driver池
driver_pool = []
pool_lock = threading.Lock()

def create_fast_driver():
    """创建优化的driver"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-browser-side-navigation')
    
    # 激进的性能优化
    options.page_load_strategy = 'eager'  # 不等待所有资源
    
    # 禁用所有可能的资源
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.media": 2,
        "profile.managed_default_content_settings.plugins": 2,
        "profile.managed_default_content_settings.popups": 2,
        "profile.managed_default_content_settings.geolocation": 2,
        "profile.managed_default_content_settings.notifications": 2,
        "profile.managed_default_content_settings.media_stream": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)  # 减少隐式等待
    driver.set_page_load_timeout(15)  # 减少超时
    
    return driver

def get_driver():
    """从池中获取或创建driver"""
    with pool_lock:
        if driver_pool:
            return driver_pool.pop()
    return create_fast_driver()

def return_driver(driver):
    """归还driver到池中"""
    with pool_lock:
        if len(driver_pool) < 3:  # 最多保留3个
            driver_pool.append(driver)
        else:
            driver.quit()

def extract_specs_fast(product_url):
    """快速提取规格"""
    driver = get_driver()
    try:
        # 访问页面
        driver.get(product_url)
        
        # 快速查找表格（不等待太久）
        time.sleep(1)  # 最小等待
        
        # 直接查找所有可能包含规格的文本
        specs = []
        
        # 策略1：快速扫描所有td元素
        cells = driver.find_elements(By.TAG_NAME, 'td')
        for cell in cells[:100]:  # 只检查前100个
            text = cell.text.strip()
            if text and len(text) > 3 and any(c.isdigit() for c in text):
                # 简单的产品编号判断
                if any(pattern in text for pattern in ['USC', 'QAAMC', 'EN-', '-', '_']):
                    specs.append(text)
                    if len(specs) >= 20:  # 找到足够多就停止
                        break
        
        # 策略2：如果没找到，尝试查找特定表格
        if not specs:
            tables = driver.find_elements(By.TAG_NAME, 'table')
            for table in tables[:2]:  # 只看前2个表格
                rows = table.find_elements(By.TAG_NAME, 'tr')[:20]
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    for cell in cells:
                        text = cell.text.strip()
                        if text and any(pattern in text for pattern in ['USC', 'QAAMC', 'EN-']):
                            specs.append(text)
        
        return list(set(specs))  # 去重
        
    finally:
        return_driver(driver)

def main():
    # 设置日志级别
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    print(f"\n🚀 快速规格提取测试")
    print("="*60)
    
    # 测试数据
    test_products = [
        'https://www.traceparts.cn/en/product/the-timken-company-double-concentric-cartridge-block-qaamc10a050s?CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175',
        'https://www.traceparts.cn/en/product/ntn-europe-usc200t20-cartridge-unit-from-grey-cast-high-temperature?CatalogPath=TRACEPARTS%3ATP01002002006&Product=34-17112021-055894',
        'https://www.traceparts.cn/en/product/jw-winco-en-561-plastic-mounting-angle-brackets-type-b-and-c?CatalogPath=TRACEPARTS%3ATP05001&Product=90-05102020-040831',
    ]
    
    # 预热：创建driver池
    print("🏊 预创建driver池...")
    start = time.time()
    for _ in range(3):
        driver = create_fast_driver()
        return_driver(driver)
    print(f"   driver池初始化: {time.time() - start:.2f}秒")
    
    # 方法1: 串行处理
    print("\n1️⃣ 串行处理")
    print("-"*60)
    
    start = time.time()
    results_serial = []
    
    for i, url in enumerate(test_products):
        t1 = time.time()
        specs = extract_specs_fast(url)
        t2 = time.time()
        results_serial.append(specs)
        print(f"   产品{i+1}: {len(specs)}个规格, 耗时{t2-t1:.2f}秒")
    
    serial_time = time.time() - start
    print(f"   串行总耗时: {serial_time:.2f}秒")
    
    # 方法2: 并行处理
    print("\n2️⃣ 并行处理")
    print("-"*60)
    
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(extract_specs_fast, url) for url in test_products]
        results_parallel = [f.result() for f in futures]
    
    parallel_time = time.time() - start
    
    for i, specs in enumerate(results_parallel):
        print(f"   产品{i+1}: {len(specs)}个规格")
    print(f"   并行总耗时: {parallel_time:.2f}秒")
    
    # 清理driver池
    print("\n🧹 清理driver池...")
    while driver_pool:
        driver = driver_pool.pop()
        driver.quit()
    
    # 性能总结
    print("\n📊 性能总结")
    print("="*60)
    print(f"串行处理: {serial_time:.2f}秒 ({serial_time/len(test_products):.2f}秒/产品)")
    print(f"并行处理: {parallel_time:.2f}秒 (加速 {serial_time/parallel_time:.1f}x)")
    
    # 与原版对比（估算）
    original_time_estimate = 5 * 60 / 3  # 原版约5分钟处理3个产品
    print(f"\n与原版对比:")
    print(f"原版估计: {original_time_estimate:.0f}秒/产品")
    print(f"优化版: {serial_time/len(test_products):.2f}秒/产品")
    print(f"性能提升: {original_time_estimate/(serial_time/len(test_products)):.1f}x")

if __name__ == '__main__':
    main() 