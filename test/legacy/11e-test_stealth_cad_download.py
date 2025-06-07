#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11e —— 强化反检测的CAD下载测试
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time
import os
import random

def test_stealth_cad_download():
    email = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
    password = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")

    print(f"🔐 开始强化反检测登录测试...")
    print(f"账号: {email}")
    print(f"密码: {'*' * len(password)}")

    with sync_playwright() as p:
        # 更强的浏览器启动配置
        browser = p.chromium.launch(
            headless=False,
            slow_mo=1000,  # 增加延迟
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-default-apps'
            ]
        )
        
        # 创建页面并配置
        page = browser.new_page()
        
        # 应用 stealth
        stealth_sync(page)
        
        # 设置更真实的用户代理和视口
        page.set_viewport_size({"width": 1366, "height": 768})
        
        # 添加额外的反检测脚本
        page.add_init_script("""
            // 移除 webdriver 属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 伪造 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // 伪造 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // 移除 automation 相关属性
            window.chrome = {
                runtime: {},
            };
            
            // 伪造权限查询
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        print("\n📄 访问登录页...")
        page.goto("https://www.traceparts.cn/en/sign-in", wait_until="networkidle")
        
        # 随机等待时间，模拟真人行为
        wait_time = random.uniform(3, 6)
        print(f"等待 {wait_time:.1f} 秒，模拟真人行为...")
        page.wait_for_timeout(int(wait_time * 1000))
        
        print("✍️ 填写邮箱...")
        email_input = page.locator("input[type='email']")
        
        # 模拟真人点击和输入
        email_input.click()
        page.wait_for_timeout(random.randint(500, 1000))
        email_input.fill("")
        page.wait_for_timeout(random.randint(200, 500))
        
        # 逐字符输入，模拟真人打字
        for char in email:
            email_input.type(char, delay=random.randint(50, 150))
        
        print("🔑 填写密码...")
        pwd_input = page.locator("input[type='password']")
        pwd_input.click()
        page.wait_for_timeout(random.randint(500, 1000))
        pwd_input.fill("")
        page.wait_for_timeout(random.randint(200, 500))
        
        # 逐字符输入密码
        for char in password:
            pwd_input.type(char, delay=random.randint(50, 150))
        
        # 触发表单验证
        pwd_input.press("Tab")
        page.wait_for_timeout(random.randint(1000, 2000))
        
        print("🚀 点击登录...")
        submit_btn = page.locator("button:has-text('Sign in')").first
        
        # 模拟鼠标移动到按钮
        submit_btn.hover()
        page.wait_for_timeout(random.randint(300, 800))
        submit_btn.click()
        
        # 等待登录响应，增加时间
        print("⏳ 等待登录响应...")
        page.wait_for_timeout(8000)
        
        # 检查登录状态
        current_url = page.url
        if "sign-in" in current_url:
            print("❌ 登录失败，仍在登录页")
            page.screenshot(path="results/login_debug/login_failed.png")
            browser.close()
            return False
        
        print(f"✅ 登录成功！当前页面: {current_url}")
        
        # 等待一段时间再访问产品页面
        print("😴 等待一段时间再访问产品页面...")
        page.wait_for_timeout(random.randint(3000, 5000))
        
        # 测试产品页面
        product_url = "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087"
        
        print(f"\n📋 访问产品页面...")
        print(f"URL: {product_url}")
        
        try:
            # 分段加载页面
            page.goto(product_url, wait_until="domcontentloaded")
            print("   ✅ DOM 内容已加载")
            page.wait_for_timeout(3000)
            
            # 等待网络空闲
            page.wait_for_load_state("networkidle")
            print("   ✅ 网络空闲")
            page.wait_for_timeout(2000)
            
            current_url = page.url
            title = page.title()
            
            print(f"   实际 URL: {current_url}")
            print(f"   页面标题: {title}")
            
            # 检查是否被重定向到登录页
            if "sign-in" in current_url.lower():
                print("   ❌ 被重定向到登录页，会话可能失效")
                return False
            
            # 初始截图
            screenshot_path = "results/login_debug/product_page_loaded.png"
            page.screenshot(path=screenshot_path)
            print(f"   📸 页面加载截图: {screenshot_path}")
            
            # 滚动页面，触发懒加载
            print("\n📜 滚动页面触发内容加载...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 4)")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3 * 2)")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1000)
            
            # 检查页面内容
            page_text = page.text_content("body").lower()
            print(f"   页面文本长度: {len(page_text)} 字符")
            
            # 寻找CAD相关内容
            cad_keywords = ["cad", "3d", "model", "download", "file", "format"]
            found_keywords = [kw for kw in cad_keywords if kw in page_text]
            print(f"   找到CAD相关关键词: {found_keywords}")
            
            # 查找所有可能的下拉选择器
            print("\n🔍 查找页面中的所有选择器...")
            selects = page.query_selector_all("select")
            print(f"   找到 {len(selects)} 个 select 元素")
            
            for i, select in enumerate(selects):
                try:
                    select_text = select.text_content() or ""
                    options = select.query_selector_all("option")
                    option_texts = [opt.text_content() for opt in options if opt.text_content()]
                    print(f"   Select {i}: {select_text[:50]} - 选项: {option_texts}")
                    
                    # 检查是否有STL选项
                    if any("stl" in opt.lower() for opt in option_texts):
                        print(f"   🎯 找到包含STL的选择器 {i}")
                        
                        # 尝试选择STL
                        try:
                            select.select_option(label="STL")
                            print("   ✅ 成功选择STL格式")
                            page.wait_for_timeout(2000)
                            break
                        except:
                            try:
                                stl_option = [opt for opt in option_texts if "stl" in opt.lower()][0]
                                select.select_option(label=stl_option)
                                print(f"   ✅ 成功选择格式: {stl_option}")
                                page.wait_for_timeout(2000)
                                break
                            except Exception as e:
                                print(f"   ⚠️ 选择失败: {e}")
                except Exception as e:
                    print(f"   ⚠️ 解析选择器失败: {e}")
            
            # 查找下载按钮
            print("\n📥 查找下载按钮...")
            buttons = page.query_selector_all("button, a, input[type='button'], input[type='submit']")
            print(f"   找到 {len(buttons)} 个可点击元素")
            
            download_candidates = []
            for i, btn in enumerate(buttons):
                try:
                    btn_text = btn.text_content() or ""
                    btn_class = btn.get_attribute("class") or ""
                    btn_id = btn.get_attribute("id") or ""
                    
                    if any(keyword in (btn_text + btn_class + btn_id).lower() 
                           for keyword in ["download", "get", "save", "export"]):
                        download_candidates.append((i, btn, btn_text))
                        print(f"   候选下载按钮 {i}: '{btn_text}' (class: {btn_class})")
                except:
                    continue
            
            # 尝试点击下载按钮
            for i, btn, btn_text in download_candidates:
                try:
                    if btn.is_visible() and btn.is_enabled():
                        print(f"   🚀 尝试点击下载按钮: '{btn_text}'")
                        
                        # 监听下载事件
                        with page.expect_download(timeout=10000) as download_info:
                            btn.click()
                            print("   ⏳ 等待下载开始...")
                        
                        download = download_info.value
                        download_path = f"results/login_debug/{download.suggested_filename}"
                        download.save_as(download_path)
                        print(f"   ✅ 文件下载成功: {download_path}")
                        break
                        
                except Exception as e:
                    print(f"   ⚠️ 下载尝试失败: {str(e)}")
                    continue
            
            # 最终截图
            final_screenshot_path = "results/login_debug/product_page_final.png"
            page.screenshot(path=final_screenshot_path)
            print(f"   📸 最终截图: {final_screenshot_path}")
            
        except Exception as e:
            print(f"   ❌ 产品页面访问失败: {str(e)}")
            page.screenshot(path="results/login_debug/product_page_error.png")
            return False
        
        print(f"\n📊 测试完成")
        input("\n🎯 测试完成，按回车关闭浏览器...")
        browser.close()
        
        return True

if __name__ == "__main__":
    test_stealth_cad_download() 