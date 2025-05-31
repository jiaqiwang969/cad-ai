#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11f —— 使用真实Chrome浏览器测试
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time
import os
import random

def test_real_chrome():
    email = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
    password = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")

    print(f"🔐 使用真实Chrome浏览器测试...")
    print(f"账号: {email}")
    print(f"密码: {'*' * len(password)}")

    with sync_playwright() as p:
        # 尝试连接到现有的Chrome实例或启动新的
        try:
            # 首先尝试连接现有Chrome（如果有的话）
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            print("✅ 连接到现有Chrome实例")
        except:
            # 如果没有现有实例，启动真实Chrome
            print("📱 启动真实Chrome浏览器...")
            browser = p.chromium.launch(
                channel="chrome",  # 使用真实Chrome而不是Chromium
                headless=False,
                slow_mo=500,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-popup-blocking',
                    '--disable-translate',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-ipc-flooding-protection',
                    # 保留更多真实浏览器特征
                    '--enable-features=NetworkService,NetworkServiceLogging',
                    '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                ]
            )
        
        # 创建新页面或使用现有页面
        if browser.contexts:
            context = browser.contexts[0]
            if context.pages:
                page = context.pages[0]
                print("✅ 使用现有页面")
            else:
                page = context.new_page()
        else:
            context = browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            )
            page = context.new_page()
        
        # 应用stealth（如果是新页面）
        try:
            stealth_sync(page)
        except:
            pass
        
        # 额外的反检测脚本
        page.add_init_script("""
            // 更完整的反检测
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 删除automation相关的window属性
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            
            // 修复Chrome对象
            if (!window.chrome) {
                window.chrome = {};
            }
            if (!window.chrome.runtime) {
                window.chrome.runtime = {};
            }
            
            // 伪造插件
            Object.defineProperty(navigator, 'plugins', {
                get: () => ({
                    0: {name: "Chrome PDF Plugin"},
                    1: {name: "Chrome PDF Viewer"},
                    2: {name: "Native Client"},
                    length: 3
                }),
            });
            
            // 伪造语言
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'zh-CN', 'zh'],
            });
            
            // 修复权限
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        print("\n📄 访问登录页...")
        page.goto("https://www.traceparts.cn/en/sign-in", wait_until="networkidle", timeout=30000)
        
        # 等待页面完全加载
        page.wait_for_timeout(5000)
        
        print("✍️ 填写邮箱...")
        email_input = page.locator("input[type='email']")
        email_input.click()
        page.wait_for_timeout(random.randint(800, 1500))
        email_input.fill("")
        
        # 更慢的输入速度
        for char in email:
            email_input.type(char, delay=random.randint(80, 200))
        
        print("🔑 填写密码...")
        pwd_input = page.locator("input[type='password']")
        pwd_input.click()
        page.wait_for_timeout(random.randint(800, 1500))
        pwd_input.fill("")
        
        for char in password:
            pwd_input.type(char, delay=random.randint(80, 200))
        
        # 模拟更自然的行为
        page.wait_for_timeout(random.randint(1000, 2000))
        pwd_input.press("Tab")
        page.wait_for_timeout(1000)
        
        print("🚀 点击登录...")
        submit_btn = page.locator("button:has-text('Sign in')").first
        
        # 更自然的鼠标移动
        submit_btn.hover()
        page.wait_for_timeout(random.randint(500, 1000))
        submit_btn.click()
        
        print("⏳ 等待登录响应...")
        page.wait_for_timeout(10000)
        
        current_url = page.url
        if "sign-in" in current_url:
            print("❌ 登录失败，仍在登录页")
            page.screenshot(path="results/login_debug/chrome_login_failed.png")
            return False
        
        print(f"✅ 登录成功！当前页面: {current_url}")
        
        # 保存登录状态的cookies
        cookies = context.cookies()
        print(f"📝 保存了 {len(cookies)} 个cookies")
        
        # 等待更长时间
        print("😴 等待更长时间再访问产品页面...")
        page.wait_for_timeout(8000)
        
        # 测试产品页面
        product_url = "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087"
        
        print(f"\n📋 访问产品页面...")
        
        try:
            # 慢慢加载页面
            page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            print("   ✅ DOM内容加载完成")
            page.wait_for_timeout(5000)
            
            # 等待更多资源
            page.wait_for_load_state("networkidle", timeout=20000)
            print("   ✅ 网络空闲")
            page.wait_for_timeout(3000)
            
            current_url = page.url
            title = page.title()
            
            print(f"   实际URL: {current_url}")
            print(f"   页面标题: {title}")
            
            if "sign-in" in current_url.lower():
                print("   ❌ 被重定向到登录页")
                return False
            
            # 截图
            screenshot_path = "results/login_debug/chrome_product_loaded.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"   📸 完整页面截图: {screenshot_path}")
            
            # 滚动并等待更长时间
            print("\n📜 慢慢滚动页面...")
            for i in range(5):
                scroll_position = (i + 1) * 0.2
                page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position})")
                page.wait_for_timeout(3000)  # 每次滚动后等待3秒
                print(f"   滚动到 {int(scroll_position * 100)}%")
            
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(2000)
            
            # 检查页面内容
            page_text = page.text_content("body")
            print(f"   页面文本长度: {len(page_text)} 字符")
            
            # 查找CAD相关内容
            cad_keywords = ["cad", "3d", "model", "download", "file", "format", "please select"]
            found_keywords = []
            for kw in cad_keywords:
                if kw in page_text.lower():
                    found_keywords.append(kw)
            print(f"   找到CAD相关关键词: {found_keywords}")
            
            # 查找所有下拉选择框
            print("\n🔍 详细分析页面选择器...")
            selects = page.query_selector_all("select")
            print(f"   找到 {len(selects)} 个选择器")
            
            for i, select in enumerate(selects):
                try:
                    select_id = select.get_attribute("id") or f"select-{i}"
                    select_class = select.get_attribute("class") or ""
                    is_visible = select.is_visible()
                    is_enabled = select.is_enabled()
                    
                    print(f"   选择器 {i}: id='{select_id}', class='{select_class}', 可见={is_visible}, 启用={is_enabled}")
                    
                    if is_visible:
                        options = select.query_selector_all("option")
                        option_texts = []
                        for opt in options:
                            text = opt.text_content()
                            value = opt.get_attribute("value")
                            if text:
                                option_texts.append(f"{text}(value:{value})")
                        
                        print(f"     选项: {option_texts}")
                        
                        # 检查STL选项
                        stl_options = [opt for opt in options if opt.text_content() and "stl" in opt.text_content().lower()]
                        if stl_options:
                            print(f"   🎯 找到STL选项！尝试选择...")
                            try:
                                stl_option = stl_options[0]
                                stl_value = stl_option.get_attribute("value")
                                stl_text = stl_option.text_content()
                                
                                select.select_option(value=stl_value)
                                print(f"   ✅ 成功选择STL: {stl_text}")
                                page.wait_for_timeout(3000)
                                
                                # 选择后截图
                                after_select_path = "results/login_debug/chrome_after_stl_select.png"
                                page.screenshot(path=after_select_path)
                                print(f"   📸 选择STL后截图: {after_select_path}")
                                break
                            except Exception as e:
                                print(f"   ⚠️ STL选择失败: {e}")
                except Exception as e:
                    print(f"   ⚠️ 分析选择器失败: {e}")
            
            # 查找下载按钮
            print("\n📥 查找下载按钮...")
            all_clickable = page.query_selector_all("button, a, input[type='button'], input[type='submit'], [onclick]")
            print(f"   找到 {len(all_clickable)} 个可点击元素")
            
            download_buttons = []
            for i, elem in enumerate(all_clickable):
                try:
                    elem_text = elem.text_content() or ""
                    elem_class = elem.get_attribute("class") or ""
                    elem_id = elem.get_attribute("id") or ""
                    elem_onclick = elem.get_attribute("onclick") or ""
                    
                    combined_text = (elem_text + elem_class + elem_id + elem_onclick).lower()
                    
                    if any(kw in combined_text for kw in ["download", "get", "export", "save"]):
                        is_visible = elem.is_visible()
                        is_enabled = elem.is_enabled()
                        download_buttons.append((i, elem, elem_text, is_visible, is_enabled))
                        print(f"   下载候选 {i}: '{elem_text}' 可见={is_visible} 启用={is_enabled}")
                except:
                    continue
            
            # 尝试下载
            for i, btn, btn_text, is_visible, is_enabled in download_buttons:
                if is_visible and is_enabled:
                    try:
                        print(f"   🚀 尝试点击: '{btn_text}'")
                        
                        with page.expect_download(timeout=15000) as download_info:
                            btn.click()
                            print("   ⏳ 等待下载...")
                        
                        download = download_info.value
                        filename = download.suggested_filename
                        download_path = f"results/login_debug/{filename}"
                        download.save_as(download_path)
                        print(f"   ✅ 下载成功: {download_path}")
                        break
                        
                    except Exception as e:
                        print(f"   ⚠️ 下载失败: {e}")
                        continue
            
            # 最终截图
            final_path = "results/login_debug/chrome_final.png"
            page.screenshot(path=final_path, full_page=True)
            print(f"   📸 最终完整截图: {final_path}")
            
        except Exception as e:
            print(f"   ❌ 产品页面测试失败: {e}")
            page.screenshot(path="results/login_debug/chrome_error.png")
            return False
        
        print(f"\n📊 Chrome测试完成")
        print("💡 提示：您可以保持浏览器开启，手动检查页面内容")
        input("\n🎯 按回车关闭...")
        
        try:
            browser.close()
        except:
            pass
        
        return True

if __name__ == "__main__":
    test_real_chrome() 