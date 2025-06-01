#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11d —— 登录成功后跳转产品页面测试
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time
import os

def test_login_and_navigate():
    email = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
    password = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")

    print(f"🔐 开始登录测试...")
    print(f"账号: {email}")
    print(f"密码: {'*' * len(password)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()
        stealth_sync(page)
        
        print("\n📄 访问登录页...")
        page.goto("https://www.traceparts.cn/en/sign-in")
        page.wait_for_timeout(3000)
        
        print("✍️ 填写邮箱...")
        email_input = page.locator("input[type='email']")
        email_input.click()
        email_input.fill("")
        email_input.type(email, delay=100)
        
        print("🔑 填写密码...")
        pwd_input = page.locator("input[type='password']") 
        pwd_input.click()
        pwd_input.fill("")
        pwd_input.type(password, delay=100)
        
        # 触发表单验证
        pwd_input.press("Tab")
        page.wait_for_timeout(1000)
        
        print("🚀 点击登录...")
        submit_btn = page.locator("button:has-text('Sign in')").first
        submit_btn.click()
        
        # 等待登录响应
        page.wait_for_timeout(5000)
        
        if "sign-in" in page.url:
            print("❌ 登录失败，仍在登录页")
            browser.close()
            return False
        
        print(f"✅ 登录成功！当前页面: {page.url}")
        
        # 测试导航到产品页面
        print("\n🔍 测试导航到产品页面...")
        
        # 测试产品页面
        product_url = "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087"
        
        print(f"\n📋 测试产品页面: {product_url}")
        
        try:
            # 导航到产品页面
            page.goto(product_url, wait_until="networkidle")
            page.wait_for_timeout(3000)
            
            current_url = page.url
            title = page.title()
            
            print(f"   实际 URL: {current_url}")
            print(f"   页面标题: {title}")
            
            # 检查是否被重定向到登录页
            if "sign-in" in current_url.lower():
                print("   ❌ 被重定向到登录页，会话可能失效")
                return False
            
            # 截图保存
            screenshot_path = "results/login_debug/product_page_initial.png"
            page.screenshot(path=screenshot_path)
            print(f"   📸 初始截图保存: {screenshot_path}")
            
            # 检查页面内容
            page_text = page.text_content("body").lower()
            
            # 检查是否包含产品相关内容
            product_indicators = ["download", "3d", "cad", "model", "technical", "specification"]
            found_indicators = [ind for ind in product_indicators if ind in page_text]
            
            if found_indicators:
                print(f"   ✅ 找到产品相关内容: {', '.join(found_indicators)}")
            else:
                print("   ⚠️ 未找到明显的产品相关内容")
            
            # 寻找CAD Model栏目
            print("\n🔍 寻找CAD Model栏目...")
            
            # 查找可能的CAD相关元素
            cad_selectors = [
                "text=CAD",
                "text=3D Model", 
                "text=Download",
                "[class*='cad']",
                "[class*='model']",
                "[class*='download']"
            ]
            
            cad_section_found = False
            for selector in cad_selectors:
                try:
                    elements = page.locator(selector).all()
                    if elements:
                        print(f"   找到CAD相关元素: {selector} ({len(elements)}个)")
                        cad_section_found = True
                        break
                except:
                    continue
            
            if cad_section_found:
                print("   ✅ 找到CAD相关栏目")
                
                # 寻找格式选择下拉框或选项
                print("\n📐 寻找格式选择器...")
                
                # 查找可能的选择器
                format_selectors = [
                    "select",
                    "[class*='select']",
                    "[class*='dropdown']", 
                    "text=please select",
                    "text=Please select",
                    "text=format",
                    "text=Format"
                ]
                
                format_selector_found = False
                for selector in format_selectors:
                    try:
                        elements = page.locator(selector).all()
                        for element in elements:
                            if element.is_visible():
                                element_text = element.text_content() or ""
                                print(f"   找到选择器: {selector} - 文本: '{element_text[:50]}'")
                                
                                # 尝试选择STL格式
                                if "select" in element_text.lower() or element.tag_name in ["select"]:
                                    print("   🎯 尝试选择STL格式...")
                                    
                                    # 如果是select元素，直接选择
                                    if element.tag_name == "select":
                                        try:
                                            element.select_option(label="STL")
                                            print("   ✅ 已选择STL格式")
                                            format_selector_found = True
                                            break
                                        except:
                                            try:
                                                element.select_option(value="stl")
                                                print("   ✅ 已选择STL格式")
                                                format_selector_found = True
                                                break
                                            except:
                                                print("   ⚠️ 未找到STL选项")
                                    else:
                                        # 尝试点击展开选择器
                                        element.click()
                                        page.wait_for_timeout(1000)
                                        
                                        # 查找STL选项
                                        stl_options = page.locator("text=STL").all()
                                        for stl_option in stl_options:
                                            if stl_option.is_visible():
                                                stl_option.click()
                                                print("   ✅ 已选择STL格式")
                                                format_selector_found = True
                                                break
                                        
                                        if format_selector_found:
                                            break
                        
                        if format_selector_found:
                            break
                    except Exception as e:
                        continue
                
                if format_selector_found:
                    # 等待选择生效
                    page.wait_for_timeout(2000)
                    
                    # 寻找下载按钮
                    print("\n📥 寻找下载按钮...")
                    download_selectors = [
                        "text=Download",
                        "text=download", 
                        "[class*='download']",
                        "button:has-text('Download')",
                        "a:has-text('Download')"
                    ]
                    
                    download_started = False
                    for selector in download_selectors:
                        try:
                            download_buttons = page.locator(selector).all()
                            for btn in download_buttons:
                                if btn.is_visible() and btn.is_enabled():
                                    print(f"   找到下载按钮: {btn.text_content()}")
                                    
                                    # 监听下载事件
                                    with page.expect_download() as download_info:
                                        btn.click()
                                        print("   🚀 点击下载按钮...")
                                    
                                    download = download_info.value
                                    download_path = f"results/login_debug/{download.suggested_filename}"
                                    download.save_as(download_path)
                                    print(f"   ✅ 文件下载成功: {download_path}")
                                    download_started = True
                                    break
                            
                            if download_started:
                                break
                        except Exception as e:
                            print(f"   ⚠️ 下载尝试失败: {str(e)}")
                            continue
                    
                    if not download_started:
                        print("   ❌ 未能启动下载")
                else:
                    print("   ❌ 未找到格式选择器")
            else:
                print("   ❌ 未找到CAD相关栏目")
            
            # 最终截图
            final_screenshot_path = "results/login_debug/product_page_final.png"
            page.screenshot(path=final_screenshot_path)
            print(f"   📸 最终截图保存: {final_screenshot_path}")
            
        except Exception as e:
            print(f"   ❌ 访问失败: {str(e)}")
            return False
        
        print(f"\n📊 测试完成")
        
        input("\n🎯 测试完成，按回车关闭浏览器...")
        browser.close()
        
        return success_count > 0

if __name__ == "__main__":
    test_login_and_navigate() 