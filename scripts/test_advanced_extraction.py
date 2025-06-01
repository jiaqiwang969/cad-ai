#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级产品提取测试
================
尝试各种方法获取所有145个产品
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from src.utils.browser_manager import create_browser_manager
from config.settings import Settings


def test_advanced_extraction():
    """测试高级提取方法"""
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("🎯 高级产品提取测试")
    print("=" * 80)
    
    manager = create_browser_manager(pool_size=1)
    
    try:
        with manager.get_browser() as driver:
            driver.get(url)
            time.sleep(3)
            
            # 方法1：检查是否有分页参数
            print("\n📋 方法1：检查URL参数")
            check_url_parameters(driver, url)
            
            # 方法2：检查是否有AJAX请求
            print("\n📋 方法2：监控网络请求")
            monitor_network_requests(driver)
            
            # 方法3：尝试修改页面大小参数
            print("\n📋 方法3：尝试修改页面大小")
            products = try_page_size_modification(driver, url)
            
            # 方法4：检查隐藏元素
            print("\n📋 方法4：查找隐藏元素")
            check_hidden_elements(driver)
            
            # 方法5：分析JavaScript变量
            print("\n📋 方法5：分析JavaScript变量")
            check_js_variables(driver)
            
            print(f"\n✅ 最终获取产品数: {len(products)}")
            
    finally:
        manager.shutdown()


def check_url_parameters(driver, base_url):
    """检查是否可以通过URL参数获取更多产品"""
    # 尝试添加常见的分页参数
    params = [
        "?page=1&size=200",
        "?limit=200",
        "?per_page=200",
        "?pageSize=200",
        "&page=1&size=200"
    ]
    
    for param in params:
        test_url = base_url + param if '?' not in param else base_url.split('?')[0] + param
        print(f"  尝试: {param}")
        
        try:
            driver.get(test_url)
            time.sleep(2)
            
            # 计算产品数
            products = driver.execute_script("""
                return document.querySelectorAll('a[href*="&Product="]').length;
            """)
            
            if products > 80:
                print(f"    ✓ 成功！获得 {products} 个产品")
                return
            else:
                print(f"    ✗ 仍然只有 {products} 个产品")
        except:
            print(f"    ✗ 参数无效")


def monitor_network_requests(driver):
    """监控网络请求，查找AJAX加载"""
    # 注入JavaScript来监控AJAX请求
    js_monitor = """
    window.ajaxRequests = [];
    
    // 监控 XMLHttpRequest
    const originalXHR = window.XMLHttpRequest;
    window.XMLHttpRequest = function() {
        const xhr = new originalXHR();
        const originalOpen = xhr.open;
        xhr.open = function(method, url) {
            window.ajaxRequests.push({method, url, type: 'XHR'});
            return originalOpen.apply(this, arguments);
        };
        return xhr;
    };
    
    // 监控 fetch
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
        window.ajaxRequests.push({url, options, type: 'fetch'});
        return originalFetch.apply(this, arguments);
    };
    """
    
    driver.execute_script(js_monitor)
    
    # 滚动触发请求
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    
    # 获取捕获的请求
    requests = driver.execute_script("return window.ajaxRequests;")
    
    if requests:
        print(f"  发现 {len(requests)} 个AJAX请求:")
        for req in requests[:5]:  # 只显示前5个
            print(f"    - {req.get('type')}: {req.get('url', '')[:80]}...")
    else:
        print("  未发现AJAX请求")


def try_page_size_modification(driver, base_url):
    """尝试通过JavaScript修改页面大小"""
    # 尝试找到并修改页面大小设置
    js_modify = """
    // 查找可能的页面大小设置
    const possibleVars = ['pageSize', 'PAGE_SIZE', 'itemsPerPage', 'limit', 'perPage'];
    
    for (let varName of possibleVars) {
        if (window[varName]) {
            console.log(`Found ${varName}: ${window[varName]}`);
            window[varName] = 200;
        }
    }
    
    // 查找React/Vue组件
    const elements = document.querySelectorAll('[data-page-size], [page-size], [limit]');
    elements.forEach(el => {
        el.setAttribute('data-page-size', '200');
        el.setAttribute('page-size', '200');
        el.setAttribute('limit', '200');
    });
    """
    
    driver.execute_script(js_modify)
    
    # 重新加载或触发更新
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # 收集所有产品
    products = driver.execute_script("""
        return Array.from(new Set(
            Array.from(document.querySelectorAll('a[href*="&Product="]'))
                .map(a => a.href)
        ));
    """)
    
    print(f"  修改后产品数: {len(products)}")
    return products


def check_hidden_elements(driver):
    """检查是否有隐藏的产品元素"""
    # 查找所有隐藏的产品相关元素
    js_hidden = """
    const hiddenProducts = [];
    
    // 查找display:none的元素
    document.querySelectorAll('[style*="display: none"], [style*="display:none"]').forEach(el => {
        const links = el.querySelectorAll('a[href*="&Product="]');
        if (links.length > 0) {
            hiddenProducts.push({
                element: el.tagName + '.' + el.className,
                productCount: links.length
            });
        }
    });
    
    // 查找visibility:hidden的元素
    document.querySelectorAll('[style*="visibility: hidden"], [style*="visibility:hidden"]').forEach(el => {
        const links = el.querySelectorAll('a[href*="&Product="]');
        if (links.length > 0) {
            hiddenProducts.push({
                element: el.tagName + '.' + el.className,
                productCount: links.length,
                visibility: 'hidden'
            });
        }
    });
    
    // 查找高度为0的元素
    document.querySelectorAll('*').forEach(el => {
        if (el.offsetHeight === 0 && el.querySelector('a[href*="&Product="]')) {
            hiddenProducts.push({
                element: el.tagName + '.' + el.className,
                productCount: el.querySelectorAll('a[href*="&Product="]').length,
                height: 0
            });
        }
    });
    
    return hiddenProducts;
    """
    
    hidden = driver.execute_script(js_hidden)
    
    if hidden:
        print(f"  发现 {len(hidden)} 个隐藏的产品容器:")
        for h in hidden[:3]:
            print(f"    - {h}")
    else:
        print("  未发现隐藏的产品元素")


def check_js_variables(driver):
    """检查JavaScript全局变量中是否有产品数据"""
    js_check = """
    const results = {};
    
    // 检查window对象
    for (let key in window) {
        if (typeof window[key] === 'object' && window[key] !== null) {
            try {
                const str = JSON.stringify(window[key]);
                if (str.includes('Product=') || str.includes('product')) {
                    results[key] = {
                        type: typeof window[key],
                        sample: str.substring(0, 100) + '...'
                    };
                }
            } catch (e) {}
        }
    }
    
    return results;
    """
    
    variables = driver.execute_script(js_check)
    
    if variables:
        print(f"  发现 {len(variables)} 个可能包含产品数据的变量:")
        for key, value in list(variables.items())[:3]:
            print(f"    - window.{key}: {value['sample']}")
    else:
        print("  未发现相关JavaScript变量")


if __name__ == '__main__':
    test_advanced_extraction() 