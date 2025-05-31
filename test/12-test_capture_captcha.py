#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 12 —— 触发 CAD 下载验证码并保存图片（Playwright 版本）
• 依赖 utils.traceparts_playwright 获取已登录浏览器上下文
• 步骤：
  1. 打开产品页
  2. 切换到 "CAD models" 选项卡
  3. 在下拉框选择首个支持格式 (优先 STL/STEP)
  4. 点击下载图标
  5. 等待验证码图片 / canvas 出现，截图保存到 results/captcha_samples/
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import Page
import logging

from utils.traceparts_playwright import get_context, ensure_login

load_dotenv()

PRODUCT_URL = os.getenv(
    "TRACEPARTS_PRODUCT_URL",
    "https://www.traceparts.cn/en/product/vuototecnica-caps-with-orings?Product=70-01102019-118491&PartNumber=00%2015%20273",
)
CAPTCHA_DIR = Path("results/captcha_samples")
CAPTCHA_DIR.mkdir(parents=True, exist_ok=True)
COOKIE_FILE = Path("results/session_cookies.json")
PREFERRED_FORMATS = ("stl", "step", "iges", "sat")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOG = logging.getLogger("test-12-playwright")

async def choose_cad_format(page: Page):
    # 尝试 <select>
    try:
        select = await page.query_selector("select:has(option:text-matches('please select', 'i'))")
        if select:
            for fmt in PREFERRED_FORMATS:
                idx = await select.evaluate(
                    "(sel, f) => [...sel.options].findIndex(o => o.textContent.toLowerCase().includes(f))",
                    fmt,
                )
                if idx != -1:
                    await select.select_option(index=idx)
                    return True
            # 退选 index 1
            await select.select_option(index=1)
            return True
    except Exception:
        pass
    # Bootstrap 自定义下拉
    try:
        btn = await page.query_selector("text=/please select/i")
        if btn:
            await btn.click()
            for fmt in PREFERRED_FORMATS:
                opt = await page.query_selector(f"ul.dropdown-menu >> text=/{fmt}/i")
                if opt:
                    await opt.click()
                    return True
            # 退而选第一项
            first = await page.query_selector("ul.dropdown-menu li >> nth=0")
            if first:
                await first.click()
                return True
    except Exception:
        pass
    return False

async def click_download(page: Page):
    selectors = [
        "button[aria-label*=download i]",
        "a[aria-label*=download i]",
        "button[class*=download i]",
        "a[class*=download i]",
        "button[title*=download i]",
        "a[title*=download i]",
        "text=/download/i",
    ]
    for sel in selectors:
        try:
            btn = await page.wait_for_selector(sel, timeout=5000)
            if btn:
                await btn.click()
                return True
        except Exception:
            continue
    return False

async def capture_captcha(page: Page):
    # 多种验证码元素
    captcha_selectors = [
        "img[src*='captcha' i]",
        "canvas[id*='captcha' i]",
        "canvas[class*='captcha' i]",
        "div[class*='captcha' i]",
    ]
    cap = None
    for sel in captcha_selectors:
        try:
            cap = await page.wait_for_selector(sel, timeout=8000)
            if cap:
                break
        except Exception:
            continue
    if cap is None:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = CAPTCHA_DIR / f"captcha_{ts}.png"
    await cap.screenshot(path=str(out_path))
    return out_path

async def main(email: str, password: str, headful: bool):
    context = await get_context(headless=not headful, cookies_path=COOKIE_FILE)
    ok = await ensure_login(context, email=email, password=password, cookies_path=COOKIE_FILE)
    if not ok:
        LOG.error("❌ 无法登录 TraceParts，停止执行")
        await context.close()
        return
    LOG.info("✅ 已确认处于登录状态，开始处理产品页…")
    page = await context.new_page()
    await page.goto(PRODUCT_URL)
    # 切到 CAD models tab
    try:
        tab = await page.query_selector("a:has-text('CAD models')")
        if tab:
            await tab.click()
            await asyncio.sleep(1)
    except Exception:
        pass
    if not await choose_cad_format(page):
        print("⚠️ 未能选择格式，可能默认已选")
    if not await click_download(page):
        print("❌ 未找到下载按钮，保存页面源码与截图调试…")
        debug_html = CAPTCHA_DIR / "debug_no_download_btn.html"
        debug_png = CAPTCHA_DIR / "debug_no_download_btn.png"
        debug_html.write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path=str(debug_png), full_page=True)
        print("📝 页面源码 =>", debug_html)
        print("📸 页面截图 =>", debug_png)
        await context.close()
        return
    out = await capture_captcha(page)
    if out:
        print("✅ 验证码已保存 =>", out)
    else:
        print("❌ 未捕获到验证码")
    await context.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=os.getenv("TRACEPARTS_EMAIL"))
    parser.add_argument("--password", default=os.getenv("TRACEPARTS_PASSWORD"))
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args()
    if not args.email or not args.password:
        parser.error("需设置 TRACEPARTS_EMAIL / TRACEPARTS_PASSWORD")
    asyncio.run(main(args.email, args.password, args.headful)) 