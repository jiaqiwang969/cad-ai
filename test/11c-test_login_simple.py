#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11c —— 极简登录测试（同步版本）
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time
import os

email = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com")
password = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")

print(f"账号: {email}")
print(f"密码: {'*' * len(password)}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    page = browser.new_page()
    stealth_sync(page)
    
    print("\n访问登录页...")
    page.goto("https://www.traceparts.cn/en/sign-in")
    
    print("等待页面加载...")
    page.wait_for_timeout(3000)
    
    print("填写邮箱...")
    email_input = page.locator("input[type='email']")
    email_input.click()
    email_input.fill("")
    email_input.type(email, delay=100)  # 模拟真人输入速度
    
    print("填写密码...")
    pwd_input = page.locator("input[type='password']") 
    pwd_input.click()
    pwd_input.fill("")
    pwd_input.type(password, delay=100)
    
    # 触发表单验证
    print("触发表单验证...")
    pwd_input.press("Tab")  # 移出密码框，触发验证
    page.wait_for_timeout(1000)
    
    print("截图保存...")
    page.screenshot(path="results/login_debug/before_submit.png")
    
    # 查找所有可能的登录按钮
    print("\n查找登录按钮...")
    buttons = page.query_selector_all("button")
    print(f"找到 {len(buttons)} 个按钮:")
    for i, btn in enumerate(buttons):
        text = btn.text_content()
        btn_type = btn.get_attribute("type")
        btn_class = btn.get_attribute("class")
        is_visible = btn.is_visible()
        is_enabled = btn.is_enabled()
        print(f"  按钮 {i}: 文本='{text}', type='{btn_type}', class='{btn_class}', 可见={is_visible}, 启用={is_enabled}")
    
    print("点击 SIGN IN...")
    
    # 尝试多种点击方式
    submit_btn = None
    
    # 方式1: 根据文本查找
    try:
        submit_btn = page.locator("button:has-text('SIGN IN')").first
        if submit_btn and submit_btn.is_visible():
            print("  找到 'SIGN IN' 按钮（文本匹配）")
            submit_btn.click()
        else:
            raise Exception("按钮不可见")
    except:
        # 方式2: 根据type查找
        try:
            submit_btn = page.locator("button[type='submit']").first
            if submit_btn and submit_btn.is_visible():
                print("  找到 submit 按钮（type匹配）")
                submit_btn.click()
            else:
                raise Exception("按钮不可见")
        except:
            # 方式3: 直接JavaScript点击
            print("  尝试JavaScript点击...")
            page.evaluate("""
                const btn = document.querySelector("button[type='submit']") || 
                           document.querySelector("button:contains('SIGN IN')") ||
                           document.querySelector("button");
                if (btn) {
                    console.log('点击按钮:', btn.textContent);
                    btn.click();
                } else {
                    console.error('找不到按钮');
                }
            """)
    
    print("等待响应...")
    page.wait_for_timeout(5000)
    
    print(f"\n当前 URL: {page.url}")
    
    # 检查是否有错误
    if "sign-in" in page.url:
        print("\n❌ 仍在登录页")
        
        # 查找所有文本内容
        all_text = page.text_content("body")
        if "password" in all_text.lower() and "incorrect" in all_text.lower():
            print("检测到密码错误提示")
        if "captcha" in all_text.lower():
            print("检测到验证码要求")
            
        page.screenshot(path="results/login_debug/after_submit.png")
        
        # 打印所有表单错误
        errors = page.query_selector_all("[class*='error'], [class*='alert'], .text-danger")
        for err in errors:
            text = err.text_content()
            if text and text.strip():
                print(f"错误: {text.strip()}")
    else:
        print("✅ 登录成功！")
    
    input("\n按回车关闭浏览器...")
    browser.close() 