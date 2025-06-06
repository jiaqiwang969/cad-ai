#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最小化规格提取测试
测试最基础的页面访问和表格提取，找出真正的性能瓶颈
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def test_minimal():
    """最小化测试"""
    print("🧪 最小化规格提取测试")
    print("="*60)
    
    # 测试URL
    test_url = 'https://www.traceparts.cn/en/product/ntn-europe-usc200t20-cartridge-unit-from-grey-cast-high-temperature?CatalogPath=TRACEPARTS%3ATP01002002006&Product=34-17112021-055894'
    
    # 1. 最基础的driver
    print("\n1️⃣ 测试最基础的Chrome配置")
    start = time.time()
    
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    
    print(f"   创建driver: {time.time() - start:.2f}秒")
    
    # 2. 访问页面
    start = time.time()
    driver.get(test_url)
    print(f"   页面加载: {time.time() - start:.2f}秒")
    
    # 3. 查找表格
    start = time.time()
    tables = driver.find_elements(By.TAG_NAME, 'table')
    print(f"   查找表格: {time.time() - start:.2f}秒 (找到 {len(tables)} 个)")
    
    # 4. 提取数据
    start = time.time()
    specs_found = 0
    for table in tables:
        if table.is_displayed():
            rows = table.find_elements(By.TAG_NAME, 'tr')
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                for cell in cells:
                    text = cell.text.strip()
                    if text and 'USC' in text:  # 简单判断是否是产品编号
                        specs_found += 1
    print(f"   提取数据: {time.time() - start:.2f}秒 (找到 {specs_found} 个可能的规格)")
    
    driver.quit()
    
    # 5. 测试优化后的driver
    print("\n2️⃣ 测试优化后的Chrome配置")
    start = time.time()
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # 禁用资源
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    print(f"   创建优化driver: {time.time() - start:.2f}秒")
    
    # 6. 访问页面（优化版）
    start = time.time()
    driver.get(test_url)
    print(f"   页面加载（优化）: {time.time() - start:.2f}秒")
    
    # 7. 快速提取
    start = time.time()
    tables = driver.find_elements(By.TAG_NAME, 'table')
    specs_found = 0
    for table in tables[:2]:  # 只检查前2个表格
        if table.is_displayed():
            rows = table.find_elements(By.TAG_NAME, 'tr')[:20]  # 只检查前20行
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                for cell in cells:
                    text = cell.text.strip()
                    if text and 'USC' in text:
                        specs_found += 1
    print(f"   快速提取: {time.time() - start:.2f}秒 (找到 {specs_found} 个规格)")
    
    driver.quit()
    
    # 8. 测试eager加载策略
    print("\n3️⃣ 测试eager页面加载策略")
    start = time.time()
    
    options = Options()
    options.add_argument('--headless')
    options.page_load_strategy = 'eager'  # 不等待所有资源
    
    driver = webdriver.Chrome(options=options)
    print(f"   创建eager driver: {time.time() - start:.2f}秒")
    
    start = time.time()
    driver.get(test_url)
    print(f"   页面加载（eager）: {time.time() - start:.2f}秒")
    
    # 等待表格出现
    start = time.time()
    import time as time_module
    for _ in range(10):
        tables = driver.find_elements(By.TAG_NAME, 'table')
        if any(t.is_displayed() for t in tables):
            break
        time_module.sleep(0.5)
    print(f"   等待表格: {time.time() - start:.2f}秒")
    
    driver.quit()
    
    print("\n✅ 测试完成")

if __name__ == '__main__':
    test_minimal() 