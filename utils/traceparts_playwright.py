#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TraceParts 会话管理 (Playwright 版本)
提供:
• get_context(headless=True) -> playwright context
• ensure_login(context, email, password, cookies_path) -> bool
  – 若 cookies 文件存在则直接加载；否则走登录流程并保存。
使用 python-dotenv 读取 .env 中的 TRACEPARTS_EMAIL / TRACEPARTS_PASSWORD.
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from playwright.async_api import async_playwright, BrowserContext, Page
from playwright_stealth import stealth_async
from dotenv import load_dotenv
import os

SIGNIN_URL = "https://www.traceparts.cn/en/sign-in"
HOME_URL = "https://www.traceparts.cn/"

load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOG = logging.getLogger("traceparts_playwright")

def _cookie_file_to_storage_state(path: Path):
    cookies = json.loads(path.read_text())
    return {"cookies": cookies, "origins": []}

async def get_context(headless: bool = True, cookies_path: Optional[Path] = None) -> BrowserContext:
    """启动浏览器 context，若给定 cookies_path 则预加载"""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    if cookies_path and cookies_path.exists():
        storage_state = _cookie_file_to_storage_state(cookies_path)
        context = await browser.new_context(storage_state=storage_state)
    else:
        context = await browser.new_context()
    return context

async def _perform_login(page: Page, email: str, password: str) -> bool:
    try:
        LOG.info(f"正在访问登录页: {SIGNIN_URL}")
        await page.goto(SIGNIN_URL, timeout=45000)
        # 隐身模式
        await stealth_async(page)
        # 填表
        LOG.info("等待邮箱输入框...")
        await page.wait_for_selector("input[type='email']", timeout=30000)
        
        # 清空并填写邮箱
        email_input = await page.query_selector("input[type='email']")
        await email_input.click()
        await email_input.fill("")
        await email_input.type(email)
        
        # 清空并填写密码
        pwd_input = await page.query_selector("input[type='password']")
        await pwd_input.click()
        await pwd_input.fill("")
        await pwd_input.type(password)
        await page.wait_for_timeout(500)  # 等待 500ms 确保输入完成
        
        # 验证输入值
        email_value = await email_input.evaluate("el => el.value")
        pwd_value = await pwd_input.evaluate("el => el.value")
        LOG.info(f"已填写账号 {email_value}, 密码长度 {len(pwd_value)}, 准备提交...")
        
        # 检查是否有错误提示
        error_msg = await page.query_selector(".error-message, .alert-danger, [role='alert']")
        if error_msg:
            error_text = await error_msg.text_content()
            LOG.warning(f"发现错误提示: {error_text}")
        
        # 尝试多种方式提交
        submit_selectors = [
            "button[type='submit']",
            "button:has-text('SIGN IN')",
            "button:has-text('Sign in')",
            "input[type='submit']",
            "button.btn-primary"
        ]
        
        submit_btn = None
        for selector in submit_selectors:
            submit_btn = await page.query_selector(selector)
            if submit_btn:
                LOG.info(f"找到提交按钮: {selector}")
                break
        
        if submit_btn:
            await submit_btn.click()
            LOG.info("已点击提交按钮，等待页面响应...")
        else:
            LOG.warning("未找到提交按钮，尝试按回车键")
            await pwd_input.press("Enter")
        
        # 等待跳转或出现错误提示
        await page.wait_for_timeout(2000)  # 等待2秒
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        # 判断是否仍停留在 sign-in
        success = "sign-in" not in page.url.lower()
        if not success:
            # 检查登录失败的具体原因
            await page.wait_for_timeout(1000)  # 等待错误提示出现
            
            # 查找各种可能的错误提示
            error_selectors = [
                ".alert-danger",
                ".error-message", 
                ".validation-error",
                "[role='alert']",
                ".text-danger",
                "span.error",
                "div.error"
            ]
            
            for selector in error_selectors:
                error_elem = await page.query_selector(selector)
                if error_elem:
                    error_text = await error_elem.text_content()
                    if error_text and error_text.strip():
                        LOG.error(f"登录错误提示: {error_text.strip()}")
                        break
            
            # 检查是否有验证码
            captcha_elem = await page.query_selector("input[name*='captcha' i], input[placeholder*='captcha' i], img[src*='captcha' i]")
            if captcha_elem:
                LOG.error("检测到验证码，需要手动输入验证码")
            
            # 保存调试截图
            debug_dir = Path("results/login_debug")
            debug_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = debug_dir / f"login_fail_{ts}.png"
            await page.screenshot(path=str(screenshot_path))
            html_path = debug_dir / f"login_fail_{ts}.html"
            html_content = await page.content()
            html_path.write_text(html_content, encoding="utf-8")
            LOG.error(f"登录失败，当前 URL: {page.url}")
            LOG.error(f"调试文件: 截图={screenshot_path}, HTML={html_path}")
        else:
            LOG.info(f"登录成功，已跳转到: {page.url}")
        return success
    except Exception as e:
        LOG.error(f"登录过程异常: {e}")
        return False

async def ensure_login(context: BrowserContext, *, email: str, password: str, cookies_path: Path) -> bool:
    """确保处于已登录状态，若无 cookie 则登录并保存"""
    page = await context.new_page()
    try:
        # 直接访问 sign-in 页面以判定登录状态；若已登录会自动跳转到 /en 或出现 302
        LOG.info(f"检查登录状态，访问: {SIGNIN_URL}")
        await page.goto(SIGNIN_URL, timeout=30000)
        LOG.info(f"当前页面 URL: {page.url}")
        email_input = await page.query_selector("input[type='email']")
        if "sign-in" not in page.url.lower() and email_input is None:
            # 已跳转走且页面没有 email 输入框 → 视为已登录
            LOG.info("检测到已登录状态（页面已跳转且无邮箱输入框）")
            return True

        # 页面仍停留在 sign-in 且出现邮箱输入框，需要执行登录
        LOG.info("未登录，开始执行登录流程...")
        ok = await _perform_login(page, email, password)
        if ok:
            cookies_path.parent.mkdir(parents=True, exist_ok=True)
            storage = await context.storage_state()
            cookies_path.write_text(json.dumps(storage["cookies"], ensure_ascii=False, indent=2))
        return ok
    finally:
        await page.close() 