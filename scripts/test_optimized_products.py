#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的产品提取测试
==================
使用更智能的策略提取所有产品
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, JavascriptException

from src.utils.browser_manager import create_browser_manager
from config.settings import Settings


def test_optimized_products():
    """测试优化的产品提取"""
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print(f"🎯 测试URL: {url}")
    print("=" * 80)
    
    manager = create_browser_manager(pool_size=1)
    
    try:
        with manager.get_browser() as driver:
            print("📋 第一步：打开页面")
            driver.get(url)
            
            # 等待页面加载
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            time.sleep(2)
            
            # 获取总产品数
            total_count = get_total_count(driver)
            print(f"\n📊 页面信息：总共 {total_count} 个产品")
            
            # 使用JavaScript提取所有产品链接
            print("\n📋 第二步：使用JavaScript快速提取")
            all_links = extract_all_products_js(driver, total_count)
            
            print(f"\n✅ 成功提取 {len(all_links)} 个产品链接")
            
            # 打印前5个和后5个
            if all_links:
                print("\n前5个产品:")
                for i, link in enumerate(all_links[:5], 1):
                    print(f"  {i}. {link}")
                
                if len(all_links) > 10:
                    print("\n后5个产品:")
                    for i, link in enumerate(all_links[-5:], len(all_links)-4):
                        print(f"  {i}. {link}")
            
            # 保存结果
            save_results(all_links)
            
    finally:
        manager.shutdown()
        print("\n✅ 测试完成")


def get_total_count(driver):
    """获取总产品数"""
    try:
        # 尝试多种选择器
        selectors = [
            ".results-infos span",
            "[class*='result'] span",
            ".breadcrumb-item.active",  # 面包屑中可能包含结果数
            "h1", "h2", "h3"  # 标题中可能包含
        ]
        
        import re
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                text = elem.text
                # 查找数字后跟"results"或单独的数字
                match = re.search(r'(\d+)\s*result', text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
        
        # 如果还是找不到，返回默认值
        print("⚠️ 无法获取准确的产品总数，使用默认值145")
        return 145
    except Exception as e:
        print(f"获取总数失败: {e}")
        return 145


def extract_all_products_js(driver, expected_count):
    """使用JavaScript快速提取所有产品"""
    all_products = set()
    
    # JavaScript代码：收集所有产品链接
    js_collect = """
    return Array.from(document.querySelectorAll('a[href*="&Product="]'))
        .map(a => a.href)
        .filter(href => href.includes('&Product='));
    """
    
    # 方法1：积极的连续滚动
    print("  - 使用积极滚动策略...")
    
    last_count = 0
    no_change_count = 0
    scroll_attempts = 0
    max_attempts = 30
    
    while scroll_attempts < max_attempts:
        # 记录当前高度
        current_height = driver.execute_script("return document.body.scrollHeight")
        
        # 滚动到底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.8)  # 等待内容加载
        
        # 收集产品
        try:
            links = driver.execute_script(js_collect)
            all_products.update(links)
        except:
            pass
        
        current_count = len(all_products)
        
        # 检查进度
        if current_count > last_count:
            print(f"    进度: {current_count}/{expected_count} 产品")
            last_count = current_count
            no_change_count = 0
        else:
            no_change_count += 1
        
        # 如果连续3次没有新产品，尝试不同策略
        if no_change_count >= 3:
            # 尝试上下滚动触发加载
            driver.execute_script("window.scrollTo(0, 0);")  # 回到顶部
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # 再到底部
            time.sleep(1)
            
            # 再次收集
            try:
                links = driver.execute_script(js_collect)
                all_products.update(links)
            except:
                pass
            
            # 如果还是没有新产品，可能已经加载完毕
            if len(all_products) == current_count:
                no_change_count += 1
                if no_change_count >= 5:
                    break
        
        # 检查是否达到目标
        if current_count >= expected_count * 0.95:  # 95%就算成功
            print(f"    ✓ 已达到目标的95%")
            break
        
        scroll_attempts += 1
        
        # 检查页面高度是否增加
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height > current_height:
            print(f"    页面高度增加: {current_height} -> {new_height}")
    
    # 方法2：中间位置滚动（有些网站在中间位置触发加载）
    if len(all_products) < expected_count:
        print(f"  - 尝试中间位置滚动 (当前: {len(all_products)})...")
        
        total_height = driver.execute_script("return document.body.scrollHeight")
        positions = [0.25, 0.5, 0.75, 0.9]  # 不同位置
        
        for pos in positions:
            scroll_to = int(total_height * pos)
            driver.execute_script(f"window.scrollTo(0, {scroll_to});")
            time.sleep(1)
            
            # 收集产品
            try:
                links = driver.execute_script(js_collect)
                all_products.update(links)
                print(f"    位置 {int(pos*100)}%: {len(all_products)} 个产品")
            except:
                pass
    
    # 方法3：模拟人工滚动（更自然）
    if len(all_products) < expected_count:
        print(f"  - 模拟人工滚动 (当前: {len(all_products)})...")
        
        # 平滑滚动脚本
        smooth_scroll = """
        const scrollStep = arguments[0];
        const scrollDelay = arguments[1];
        let scrolled = 0;
        const scrollInterval = setInterval(() => {
            window.scrollBy(0, scrollStep);
            scrolled += scrollStep;
            if (scrolled >= arguments[2]) {
                clearInterval(scrollInterval);
            }
        }, scrollDelay);
        """
        
        # 执行平滑滚动
        total_scroll = driver.execute_script("return document.body.scrollHeight - window.innerHeight")
        driver.execute_script(smooth_scroll, 100, 50, total_scroll)
        time.sleep(3)  # 等待滚动完成
        
        # 最后收集
        try:
            links = driver.execute_script(js_collect)
            all_products.update(links)
            print(f"    平滑滚动后: {len(all_products)} 个产品")
        except:
            pass
    
    return list(all_products)


def save_results(links):
    """保存结果到文件"""
    try:
        output_file = Settings.RESULTS_DIR / 'debug' / 'extracted_products.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(links),
                'products': links
            }, f, indent=2, ensure_ascii=False)
        print(f"\n💾 结果已保存到: {output_file}")
    except Exception as e:
        print(f"保存失败: {e}")


if __name__ == '__main__':
    test_optimized_products() 