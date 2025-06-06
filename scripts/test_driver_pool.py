#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试driver池性能
比较每次创建新driver vs 复用driver的性能差异
"""

import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

class DriverPool:
    """简单的driver池实现"""
    def __init__(self, size=3):
        self.pool = queue.Queue(maxsize=size)
        self.size = size
        self._initialize_pool()
    
    def _initialize_pool(self):
        """初始化driver池"""
        print(f"🏊 初始化driver池 (size={self.size})...")
        for i in range(self.size):
            start = time.time()
            driver = self._create_driver()
            self.pool.put(driver)
            print(f"   Driver {i+1} 创建耗时: {time.time() - start:.2f}秒")
    
    def _create_driver(self):
        """创建优化的driver"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # 禁用资源加载
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        return webdriver.Chrome(options=options)
    
    def get(self, timeout=None):
        """获取一个driver"""
        return self.pool.get(timeout=timeout)
    
    def put(self, driver):
        """归还driver到池中"""
        self.pool.put(driver)
    
    def close_all(self):
        """关闭所有driver"""
        while not self.pool.empty():
            try:
                driver = self.pool.get_nowait()
                driver.quit()
            except:
                pass

def extract_specs_new_driver(url):
    """每次创建新driver的方式"""
    start_total = time.time()
    
    # 创建driver
    start = time.time()
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2,
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    create_time = time.time() - start
    
    # 访问页面
    start = time.time()
    driver.get(url)
    load_time = time.time() - start
    
    # 提取规格
    start = time.time()
    specs = 0
    tables = driver.find_elements(By.TAG_NAME, 'table')
    for table in tables:
        if table.is_displayed():
            rows = table.find_elements(By.TAG_NAME, 'tr')[:20]
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, 'td')
                for cell in cells:
                    if 'USC' in cell.text or 'QAAMC' in cell.text or 'EN-' in cell.text:
                        specs += 1
    extract_time = time.time() - start
    
    # 关闭driver
    start = time.time()
    driver.quit()
    close_time = time.time() - start
    
    total_time = time.time() - start_total
    
    return {
        'specs': specs,
        'create_time': create_time,
        'load_time': load_time,
        'extract_time': extract_time,
        'close_time': close_time,
        'total_time': total_time
    }

def extract_specs_with_pool(url, driver):
    """使用driver池的方式"""
    start_total = time.time()
    
    # 访问页面
    start = time.time()
    driver.get(url)
    load_time = time.time() - start
    
    # 提取规格
    start = time.time()
    specs = 0
    tables = driver.find_elements(By.TAG_NAME, 'table')
    for table in tables:
        if table.is_displayed():
            rows = table.find_elements(By.TAG_NAME, 'tr')[:20]
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, 'td')
                for cell in cells:
                    if 'USC' in cell.text or 'QAAMC' in cell.text or 'EN-' in cell.text:
                        specs += 1
    extract_time = time.time() - start
    
    total_time = time.time() - start_total
    
    return {
        'specs': specs,
        'load_time': load_time,
        'extract_time': extract_time,
        'total_time': total_time
    }

def main():
    """主测试函数"""
    print("🧪 Driver池性能测试")
    print("="*60)
    
    # 测试URL
    test_urls = [
        'https://www.traceparts.cn/en/product/the-timken-company-double-concentric-cartridge-block-qaamc10a050s?CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175',
        'https://www.traceparts.cn/en/product/ntn-europe-usc200t20-cartridge-unit-from-grey-cast-high-temperature?CatalogPath=TRACEPARTS%3ATP01002002006&Product=34-17112021-055894',
        'https://www.traceparts.cn/en/product/jw-winco-en-561-plastic-mounting-angle-brackets-type-b-and-c?CatalogPath=TRACEPARTS%3ATP05001&Product=90-05102020-040831',
    ]
    
    # 测试1: 每次创建新driver（串行）
    print("\n1️⃣ 测试: 每次创建新driver（串行）")
    print("-"*60)
    
    results1 = []
    start_test1 = time.time()
    
    for i, url in enumerate(test_urls):
        print(f"   处理产品 {i+1}...")
        result = extract_specs_new_driver(url)
        results1.append(result)
        print(f"     规格: {result['specs']}, 总耗时: {result['total_time']:.2f}秒")
        print(f"     (创建: {result['create_time']:.2f}s, 加载: {result['load_time']:.2f}s, 提取: {result['extract_time']:.2f}s, 关闭: {result['close_time']:.2f}s)")
    
    total_time1 = time.time() - start_test1
    print(f"   总耗时: {total_time1:.2f}秒")
    
    # 测试2: 使用driver池（串行）
    print("\n2️⃣ 测试: 使用driver池（串行）")
    print("-"*60)
    
    pool = DriverPool(size=1)
    results2 = []
    start_test2 = time.time()
    
    for i, url in enumerate(test_urls):
        print(f"   处理产品 {i+1}...")
        driver = pool.get()
        result = extract_specs_with_pool(url, driver)
        pool.put(driver)
        results2.append(result)
        print(f"     规格: {result['specs']}, 总耗时: {result['total_time']:.2f}秒")
        print(f"     (加载: {result['load_time']:.2f}s, 提取: {result['extract_time']:.2f}s)")
    
    total_time2 = time.time() - start_test2
    print(f"   总耗时: {total_time2:.2f}秒 (不含初始化)")
    
    # 测试3: 每次创建新driver（并行）
    print("\n3️⃣ 测试: 每次创建新driver（并行）")
    print("-"*60)
    
    start_test3 = time.time()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(extract_specs_new_driver, url) for url in test_urls]
        results3 = [f.result() for f in futures]
    
    total_time3 = time.time() - start_test3
    
    for i, result in enumerate(results3):
        print(f"   产品 {i+1}: {result['specs']} 规格, {result['total_time']:.2f}秒")
    print(f"   总耗时: {total_time3:.2f}秒")
    
    # 测试4: 使用driver池（并行）
    print("\n4️⃣ 测试: 使用driver池（并行）")
    print("-"*60)
    
    pool2 = DriverPool(size=3)
    start_test4 = time.time()
    
    def process_with_pool(url):
        driver = pool2.get()
        try:
            result = extract_specs_with_pool(url, driver)
            return result
        finally:
            pool2.put(driver)
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_with_pool, url) for url in test_urls]
        results4 = [f.result() for f in futures]
    
    total_time4 = time.time() - start_test4
    
    for i, result in enumerate(results4):
        print(f"   产品 {i+1}: {result['specs']} 规格, {result['total_time']:.2f}秒")
    print(f"   总耗时: {total_time4:.2f}秒 (不含初始化)")
    
    # 清理
    pool.close_all()
    pool2.close_all()
    
    # 性能对比
    print("\n📊 性能对比")
    print("="*60)
    print(f"1. 每次新建driver（串行）: {total_time1:.2f}秒")
    print(f"2. 使用driver池（串行）: {total_time2:.2f}秒 (加速 {total_time1/total_time2:.1f}x)")
    print(f"3. 每次新建driver（并行）: {total_time3:.2f}秒 (加速 {total_time1/total_time3:.1f}x)")
    print(f"4. 使用driver池（并行）: {total_time4:.2f}秒 (加速 {total_time1/total_time4:.1f}x)")
    
    # 计算平均driver创建时间
    avg_create_time = sum(r['create_time'] for r in results1) / len(results1)
    print(f"\n💡 平均driver创建时间: {avg_create_time:.2f}秒")
    print(f"   使用driver池可节省: {avg_create_time * len(test_urls):.2f}秒")

if __name__ == '__main__':
    main() 