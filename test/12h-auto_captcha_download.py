#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 12h —— 自动识别验证码并完成 CAD 文件下载（Playwright + OCR）
------------------------------------------------------------
步骤概览：
1. 复用 utils.traceparts_playwright 管理会话，确保已登录。
2. 打开指定产品页，切到"CAD models"标签并选择首选格式（STEP/STL/IGES…）。
3. 点击下载按钮，触发验证码。
4. 捕获验证码（支持 <img src="data:image/png;base64,..."> 或普通 <img>/<canvas> 元素），使用 utils.captcha_solver 自动识别。
5. 将识别结果填入验证码输入框并提交；若识别失败自动重试 2 次（共 3 次）。
6. 监听 download 事件并保存文件到 results/downloads/ 目录。

依赖环境：
• requirements.txt 已包含 tesseract OCR 相关依赖（pytesseract、opencv-python、Pillow）
• 本机需安装 Tesseract 可执行文件，或在环境变量 TESSERACT_CMD 指定路径。
"""

import asyncio
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from playwright.async_api import Page

from utils.traceparts_playwright import get_context, ensure_login
from utils.captcha_solver import solve_base64_captcha, solve_file

load_dotenv()

PRODUCT_URL = os.getenv(
    "TRACEPARTS_PRODUCT_URL",
    "https://www.traceparts.cn/en/product/rs-pro-abs-plastic-sheet-stock1220x610x15mm?CatalogPath=TRACEPARTS%3ATP05009&Product=90-03062024-057087",
)
DOWNLOAD_DIR = Path("results/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
COOKIE_FILE = Path("results/session_cookies.json")
PREFERRED_FORMATS = ("step", "stl", "iges", "sat")
MAX_CAPTCHA_TRY = 3

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOG = logging.getLogger("test-12h")

# --------------- 辅助函数 -----------------

async def choose_cad_format(page: Page) -> bool:
    """选择下拉框中的 CAD 格式，优先选择常用格式"""
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
            # 未命中首选格式 → 选择第二项（index=1）
            await select.select_option(index=1)
            return True
    except Exception:
        pass
    # 针对 Bootstrap 自定义下拉
    try:
        btn = await page.query_selector("text=/please select/i")
        if btn:
            await btn.click()
            for fmt in PREFERRED_FORMATS:
                opt = await page.query_selector(f"ul.dropdown-menu >> text=/{fmt}/i")
                if opt:
                    await opt.click()
                    return True
            first = await page.query_selector("ul.dropdown-menu li >> nth=0")
            if first:
                await first.click()
                return True
    except Exception:
        pass
    return False

async def click_download_button(page: Page) -> bool:
    selectors = [
        "#direct-cad-download",
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
            btn = await page.wait_for_selector(sel, timeout=6000)
            if btn:
                # 检查 disabled
                disabled = await btn.get_attribute("disabled")
                classes = (await btn.get_attribute("class")) or ""
                if disabled == "disabled" or "disabled" in classes.lower():
                    continue
                await btn.click()
                return True
        except Exception:
            continue
    return False

async def capture_captcha_element(page: Page):
    captcha_selectors = [
        "img[src*='captcha' i]",
        "canvas[id*='captcha' i]",
        "canvas[class*='captcha' i]",
        "div[class*='captcha' i] img",
    ]
    for sel in captcha_selectors:
        try:
            cap = await page.wait_for_selector(sel, timeout=8000)
            if cap:
                return cap
        except Exception:
            continue
    return None

async def solve_captcha(page: Page) -> Optional[str]:
    """捕获并 OCR 识别验证码，返回识别文本。若失败返回 None"""
    cap_elem = await capture_captcha_element(page)
    if cap_elem is None:
        LOG.warning("⚠️ 未发现验证码元素")
        return None

    # 情况 A: <img src="data:image/png;base64,...">
    try:
        src = await cap_elem.get_attribute("src")
        if src and src.startswith("data:image") and ";base64," in src:
            b64_str = src.split(",", 1)[1]
            text = solve_base64_captcha(b64_str)
            LOG.info(f"📖 OCR(base64) => '{text}'")
            return text
    except Exception:
        pass

    # 情况 B: 普通 <img> / <canvas> => 截图文件识别
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    img_path = DOWNLOAD_DIR.parent / "captcha_samples" / f"cap_{ts}.png"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    await cap_elem.screenshot(path=str(img_path))
    text = solve_file(str(img_path))
    LOG.info(f"📖 OCR(file) => '{text}', 图片 => {img_path}")
    return text

async def fill_captcha_and_submit(page: Page, text: str) -> bool:
    """填写验证码并再次点击下载/提交"""
    # 输入框
    input_sel = "input[type='text']:below(img[src*='captcha']), input[name*='captcha' i]"
    cap_input = await page.query_selector(input_sel)
    if not cap_input:
        LOG.error("❌ 未找到验证码输入框")
        return False
    await cap_input.click()
    await cap_input.fill("")
    await cap_input.type(text)
    # 再次点击下载
    ok = await click_download_button(page)
    return ok

# --------------- 主流程 -----------------

async def main(email: str, password: str, headful: bool):
    context = await get_context(headless=not headful, cookies_path=COOKIE_FILE)
    ok = await ensure_login(context, email=email, password=password, cookies_path=COOKIE_FILE)
    if not ok:
        LOG.error("❌ 登录失败，退出…")
        await context.close()
        return
    page = await context.new_page()
    await page.goto(PRODUCT_URL)
    # 切换到 CAD tab
    try:
        tab = await page.query_selector("a:has-text('CAD models')")
        if tab:
            await tab.click()
            await asyncio.sleep(1)
    except Exception:
        pass

    if not await choose_cad_format(page):
        LOG.warning("⚠️ CAD 格式选择失败，可能已有默认格式…")

    if not await click_download_button(page):
        LOG.error("❌ 首次点击下载按钮失败…")
        await context.close()
        return

    # 处理验证码
    for attempt in range(1, MAX_CAPTCHA_TRY + 1):
        LOG.info(f"🔑 处理验证码 (第 {attempt}/{MAX_CAPTCHA_TRY} 次)…")
        text = await solve_captcha(page)
        if not text or len(text) < 4:
            LOG.warning("⚠️ 识别结果无效，刷新验证码重试…")
            # 刷新验证码
            refresh_sel = "button:has-text('refresh'), .captcha-refresh, a:has-text('refresh')"
            try:
                refresh_btn = await page.query_selector(refresh_sel)
                if refresh_btn:
                    await refresh_btn.click()
                    await asyncio.sleep(1)
            except Exception:
                pass
            continue
        if await fill_captcha_and_submit(page, text):
            LOG.info("⏳ 已提交验证码，等待下载…")
            break
    else:
        LOG.error("❌ 多次识别验证码失败…")
        await context.close()
        return

    # 监听下载
    download: Optional[object] = None

    def _dl_handler(d):
        nonlocal download
        download = d
    page.once("download", _dl_handler)

    # 等待下载完成或超时
    try:
        await page.wait_for_event("download", timeout=60000)
    except Exception:
        pass

    if download:
        fname = download.suggested_filename
        out_path = DOWNLOAD_DIR / fname
        await download.save_as(str(out_path))
        LOG.info(f"✅ CAD 文件已下载 => {out_path}")
    else:
        LOG.error("❌ 未捕获到下载事件，可能验证码填写有误…")

    await context.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TraceParts 自动识别验证码并下载 CAD")
    parser.add_argument("--email", default=os.getenv("TRACEPARTS_EMAIL"))
    parser.add_argument("--password", default=os.getenv("TRACEPARTS_PASSWORD"))
    parser.add_argument("--headful", action="store_true", help="使用可见浏览器模式")
    args = parser.parse_args()
    if not args.email or not args.password:
        parser.error("需设置 TRACEPARTS_EMAIL / TRACEPARTS_PASSWORD")

    asyncio.run(main(args.email, args.password, args.headful)) 