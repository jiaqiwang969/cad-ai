#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11 —— Playwright 登录 + 会话持久化
运行方式：
$ python test/11-test_login_and_session.py --headful
或提前在 .env / 环境变量中设置 TRACEPARTS_EMAIL / TRACEPARTS_PASSWORD，再用 make test-11。
"""

import asyncio
import os
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

from utils.traceparts_playwright import get_context, ensure_login

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
LOG = logging.getLogger("test-11-playwright")

TEST_PRODUCT = "https://www.traceparts.cn/en/product/vuototecnica-caps-with-orings?Product=70-01102019-118491&PartNumber=00%2015%20273"
COOKIE_FILE = Path("results/session_cookies.json")

load_dotenv()

async def main(email: str, password: str, headful: bool):
    context = await get_context(headless=not headful, cookies_path=COOKIE_FILE)
    ok = await ensure_login(context, email=email, password=password, cookies_path=COOKIE_FILE)
    if not ok:
        LOG.error("❌ 登录失败，请检查账号/验证码")
        await context.close()
        return
    LOG.info("✅ 已登录，前往示例产品页验证会话…")
    page = await context.new_page()
    await page.goto(TEST_PRODUCT)
    await asyncio.sleep(3)
    LOG.info("示例产品页标题: %s", await page.title())
    await context.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=os.getenv("TRACEPARTS_EMAIL"), help="账号邮箱")
    parser.add_argument("--password", default=os.getenv("TRACEPARTS_PASSWORD"), help="密码")
    parser.add_argument("--headful", action="store_true", help="显示浏览器窗口")
    args = parser.parse_args()
    if not args.email or not args.password:
        parser.error("需要提供 --email/--password 或在环境变量/ .env 中设置 TRACEPARTS_EMAIL/PASSWORD")
    asyncio.run(main(args.email, args.password, args.headful)) 