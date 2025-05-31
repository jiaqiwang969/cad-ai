#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11b —— 手动登录调试版本
用于调试登录问题，会在关键步骤暂停等待
"""

import asyncio
import os
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from dotenv import load_dotenv

load_dotenv()

async def main():
    email = os.getenv("TRACEPARTS_EMAIL", "SearcherKerry36154@hotmail.com") 
    password = os.getenv("TRACEPARTS_PASSWORD", "Vsn220mh@")
    
    print(f"账号: {email}")
    print(f"密码: {'*' * len(password)} (长度: {len(password)})")
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=False,  # 强制显示浏览器
        slow_mo=1000     # 每个动作延迟1秒，便于观察
    )
    
    context = await browser.new_context()
    page = await context.new_page()
    
    # 应用隐身模式
    await stealth_async(page)
    
    print("\n[1] 访问登录页...")
    await page.goto("https://www.traceparts.cn/en/sign-in")
    await asyncio.sleep(2)
    
    print("\n[2] 填写邮箱...")
    email_input = await page.query_selector("input[type='email']")
    if email_input:
        await email_input.click()
        await email_input.type(email, delay=100)  # 模拟人工输入速度
    else:
        print("❌ 找不到邮箱输入框！")
        
    await asyncio.sleep(1)
    
    print("\n[3] 填写密码...")
    pwd_input = await page.query_selector("input[type='password']")
    if pwd_input:
        await pwd_input.click()
        await pwd_input.type(password, delay=100)
    else:
        print("❌ 找不到密码输入框！")
        
    await asyncio.sleep(1)
    
    # 检查页面上是否有验证码
    captcha = await page.query_selector("img[src*='captcha' i], input[name*='captcha' i]")
    if captcha:
        print("\n⚠️ 检测到验证码，请手动输入验证码...")
        await asyncio.sleep(30)  # 等待30秒让用户输入验证码
    
    print("\n[4] 查找提交按钮...")
    submit_btns = await page.query_selector_all("button")
    for btn in submit_btns:
        text = await btn.text_content()
        print(f"   找到按钮: {text}")
        
    print("\n[5] 点击登录按钮...")
    submit_btn = await page.query_selector("button[type='submit'], button:has-text('SIGN IN')")
    if submit_btn:
        await submit_btn.click()
    else:
        print("❌ 找不到提交按钮！")
    
    print("\n[6] 等待页面响应...")
    await asyncio.sleep(5)
    
    print(f"\n最终 URL: {page.url}")
    
    if "sign-in" not in page.url:
        print("✅ 登录成功！")
    else:
        print("❌ 登录失败，仍在登录页")
        
        # 查找错误提示
        errors = await page.query_selector_all(".alert, .error, [role='alert']")
        for err in errors:
            text = await err.text_content()
            if text and text.strip():
                print(f"错误提示: {text.strip()}")
    
    print("\n按 Ctrl+C 关闭浏览器...")
    await asyncio.sleep(300)  # 保持浏览器打开5分钟

if __name__ == "__main__":
    asyncio.run(main()) 