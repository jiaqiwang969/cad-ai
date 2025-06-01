#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试Show More Results按钮
========================
详细分析按钮的位置和状态
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils.browser_manager import create_browser_manager


def test_show_more_debug():
    """调试Show More按钮"""
    url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-transfer-switching-equipment-tse?CatalogPath=TRACEPARTS%3ATP09004001017"
    
    print("🔍 调试 Show More Results 按钮")
    print("=" * 80)
    
    manager = create_browser_manager(pool_size=1)
    
    try:
        with manager.get_browser() as driver:
            driver.get(url)
            time.sleep(2)
            
            # 1. 首先滚动页面，看看产品数如何变化
            print("\n📋 步骤1: 测试滚动加载")
            js_count = "return document.querySelectorAll('a[href*=\"&Product=\"]').length;"
            
            for i in range(5):
                count = driver.execute_script(js_count)
                height = driver.execute_script("return document.body.scrollHeight")
                print(f"  滚动前 - 产品数: {count}, 页面高度: {height}")
                
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                
                new_count = driver.execute_script(js_count)
                new_height = driver.execute_script("return document.body.scrollHeight")
                print(f"  滚动后 - 产品数: {new_count}, 页面高度: {new_height}")
                
                if new_count > count:
                    print(f"    ✓ 新增 {new_count - count} 个产品")
                else:
                    print(f"    - 没有新产品")
                print()
            
            # 2. 查找所有可能的按钮
            print("\n📋 步骤2: 查找所有可能的按钮")
            
            # 查找所有按钮元素
            buttons_info = driver.execute_script("""
                const buttons = [];
                
                // 查找所有button元素
                document.querySelectorAll('button').forEach(btn => {
                    const text = btn.textContent.trim().toLowerCase();
                    if (text.includes('show') || text.includes('more') || text.includes('load')) {
                        buttons.push({
                            tag: 'button',
                            text: btn.textContent.trim(),
                            visible: btn.offsetParent !== null,
                            position: btn.getBoundingClientRect(),
                            classes: btn.className
                        });
                    }
                });
                
                // 查找所有a元素
                document.querySelectorAll('a').forEach(link => {
                    const text = link.textContent.trim().toLowerCase();
                    if (text.includes('show') || text.includes('more') || text.includes('load')) {
                        buttons.push({
                            tag: 'a',
                            text: link.textContent.trim(),
                            visible: link.offsetParent !== null,
                            position: link.getBoundingClientRect(),
                            classes: link.className
                        });
                    }
                });
                
                // 查找所有div/span元素（可能是自定义按钮）
                document.querySelectorAll('div, span').forEach(elem => {
                    const text = elem.textContent.trim().toLowerCase();
                    if ((text.includes('show') && text.includes('more')) || 
                        (text.includes('load') && text.includes('more'))) {
                        // 检查是否有点击事件
                        const hasClick = elem.onclick !== null || 
                                       elem.getAttribute('onclick') !== null ||
                                       elem.style.cursor === 'pointer';
                        if (hasClick || elem.className.includes('button') || elem.className.includes('btn')) {
                            buttons.push({
                                tag: elem.tagName.toLowerCase(),
                                text: elem.textContent.trim(),
                                visible: elem.offsetParent !== null,
                                position: elem.getBoundingClientRect(),
                                classes: elem.className
                            });
                        }
                    }
                });
                
                return buttons;
            """)
            
            if buttons_info:
                print(f"  找到 {len(buttons_info)} 个可能的按钮:")
                for btn in buttons_info:
                    print(f"    - {btn['tag']}: '{btn['text']}'")
                    print(f"      可见: {btn['visible']}")
                    print(f"      位置: top={btn['position']['top']:.0f}, left={btn['position']['left']:.0f}")
                    print(f"      类名: {btn['classes']}")
            else:
                print("  ❌ 没有找到相关按钮")
            
            # 3. 尝试点击找到的按钮
            if buttons_info:
                print("\n📋 步骤3: 尝试点击按钮")
                
                for btn_info in buttons_info:
                    if btn_info['visible']:
                        try:
                            # 根据文本查找元素
                            selector = f"//{btn_info['tag']}[contains(text(), '{btn_info['text']}')]"
                            button = driver.find_element(By.XPATH, selector)
                            
                            # 滚动到按钮位置
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            time.sleep(0.5)
                            
                            # 点击前的产品数
                            before_count = driver.execute_script(js_count)
                            
                            # 点击
                            driver.execute_script("arguments[0].click();", button)
                            print(f"  ✓ 点击了 '{btn_info['text']}'")
                            
                            # 等待加载
                            time.sleep(2)
                            
                            # 点击后的产品数
                            after_count = driver.execute_script(js_count)
                            print(f"    产品数: {before_count} -> {after_count}")
                            
                            if after_count > before_count:
                                print(f"    ✅ 成功！新增 {after_count - before_count} 个产品")
                                break
                                
                        except Exception as e:
                            print(f"  ✗ 点击 '{btn_info['text']}' 失败: {type(e).__name__}")
            
            # 最终统计
            final_count = driver.execute_script(js_count)
            print(f"\n📊 最终产品数: {final_count}")
            
    finally:
        manager.shutdown()


if __name__ == '__main__':
    test_show_more_debug() 