#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断产品加载问题
===============
检查Show More按钮、产品数量变化等
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import random

# 导入配置
from config.settings import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("debug-product-loading")


def debug_product_loading():
    """诊断产品加载问题"""
    
    # 测试URL
    test_url = "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-flanged-block-bearings?CatalogPath=TRACEPARTS%3ATP01002002002"
    
    with sync_playwright() as p:
        # 创建浏览器（有头模式便于观察）
        browser = p.chromium.launch(
            headless=False,
            slow_mo=500,  # 慢动作便于观察
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        stealth_sync(page)
        
        try:
            # 简单登录（快速版本）
            LOG.info("🔐 快速登录...")
            auth_config = Settings.AUTH['accounts'][0]
            
            page.goto("https://www.traceparts.cn/en/sign-in")
            page.fill("input[type='email']", auth_config['email'])
            page.fill("input[type='password']", auth_config['password'])
            page.click("button:has-text('Sign in')")
            page.wait_for_timeout(3000)
            
            # 访问测试页面
            LOG.info(f"🌐 访问测试页面...")
            page.goto(test_url)
            page.wait_for_timeout(5000)
            
            # 初始状态检查
            initial_products = len(page.query_selector_all("a[href*='&Product=']"))
            LOG.info(f"📊 初始产品数量: {initial_products}")
            
            # 检查页面结构
            LOG.info("🔍 检查页面结构...")
            
            # 查找所有可能的按钮
            all_buttons = page.query_selector_all("button")
            LOG.info(f"📱 页面总按钮数: {len(all_buttons)}")
            
            show_more_candidates = []
            for i, btn in enumerate(all_buttons[:20]):  # 只检查前20个按钮
                try:
                    text = btn.text_content() or ""
                    class_name = btn.get_attribute("class") or ""
                    if any(keyword in text.lower() for keyword in ["show", "more", "load"]) or \
                       any(keyword in class_name.lower() for keyword in ["show", "more", "load"]):
                        show_more_candidates.append({
                            'index': i,
                            'text': text.strip(),
                            'class': class_name,
                            'visible': btn.is_visible(),
                            'enabled': btn.is_enabled()
                        })
                except:
                    continue
            
            LOG.info(f"🎯 找到 {len(show_more_candidates)} 个Show More候选按钮:")
            for candidate in show_more_candidates:
                LOG.info(f"   按钮 {candidate['index']}: '{candidate['text']}' | class='{candidate['class']}' | visible={candidate['visible']} | enabled={candidate['enabled']}")
            
            # 滚动测试
            LOG.info("📜 开始滚动测试...")
            for scroll_test in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                page.wait_for_timeout(2000)
                
                current_products = len(page.query_selector_all("a[href*='&Product=']"))
                LOG.info(f"   滚动 {scroll_test + 1}: 产品数量 = {current_products}")
                
                if current_products != initial_products:
                    LOG.info("✅ 滚动触发了产品数量变化！")
                    break
            
            # 尝试点击第一个Show More候选按钮
            if show_more_candidates:
                LOG.info("👆 尝试点击第一个Show More候选按钮...")
                try:
                    first_candidate = show_more_candidates[0]
                    button = all_buttons[first_candidate['index']]
                    
                    button.scroll_into_view_if_needed()
                    page.wait_for_timeout(1000)
                    
                    before_click = len(page.query_selector_all("a[href*='&Product=']"))
                    LOG.info(f"   点击前产品数: {before_click}")
                    
                    button.click()
                    page.wait_for_timeout(3000)
                    
                    after_click = len(page.query_selector_all("a[href*='&Product=']"))
                    LOG.info(f"   点击后产品数: {after_click}")
                    
                    if after_click > before_click:
                        LOG.info("✅ 按钮点击成功增加了产品！")
                    else:
                        LOG.warning("⚠️ 按钮点击没有增加产品")
                        
                except Exception as e:
                    LOG.error(f"❌ 点击按钮失败: {e}")
            
            # 检查网络请求
            LOG.info("🌐 检查页面网络活动...")
            
            # 等待用户观察
            LOG.info("⏸️ 脚本暂停，请在浏览器中手动测试...")
            LOG.info("   1. 尝试手动滚动")
            LOG.info("   2. 查找并点击Show More按钮")
            LOG.info("   3. 观察产品数量变化")
            LOG.info("   按 Ctrl+C 结束脚本")
            
            try:
                while True:
                    time.sleep(5)
                    current_products = len(page.query_selector_all("a[href*='&Product=']"))
                    LOG.info(f"   当前产品数量: {current_products}")
            except KeyboardInterrupt:
                LOG.info("🛑 用户中断，结束诊断")
            
        finally:
            browser.close()


if __name__ == "__main__":
    debug_product_loading()