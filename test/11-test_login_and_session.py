#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 11  —— 登录 + 会话持久化示例

用法：
$ python test/11-test_login_and_session.py --email xxx --password yyy [--save cookies.json]
或提前设置环境变量 TRACEPARTS_EMAIL / TRACEPARTS_PASSWORD，直接运行 make test-11。

流程：
1. 通过 Selenium 打开 TraceParts 登录页，输入邮箱/密码，提交。
2. 等待跳转首页判定登录成功；随后将 cookies 保存到 results/session_cookies.json（或指定文件）。
3. 演示复用同一会话访问示例产品页，验证无需再登录。
"""

import os
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
LOG = logging.getLogger(__name__)

LOGIN_URL = "https://www.traceparts.cn/en/login"
TEST_PRODUCT = "https://www.traceparts.cn/en/product/vuototecnica-caps-with-orings?Product=70-01102019-118491&PartNumber=00%2015%20273"


def build_driver(headful: bool = False, debug_port: int = 9222):
    opts = Options()
    if not headful:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1500,1000")
    # 若要调试，可打开远程调试端口
    # opts.add_argument(f"--remote-debugging-port={debug_port}")
    driver = webdriver.Chrome(options=opts)
    return driver


def login(driver: "webdriver.Chrome", email: str, password: str) -> bool:
    driver.get(LOGIN_URL)
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "email")))
        driver.find_element(By.ID, "email").send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        # 登录按钮
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        # 等待首页或个人中心出现
        WebDriverWait(driver, 15).until(EC.url_changes(LOGIN_URL))
        LOG.info("✅ 登录成功，当前 URL: %s", driver.current_url)
        return True
    except Exception as e:
        LOG.error("登录失败: %s", e)
        debug_dir = Path("results/login_debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        driver.save_screenshot(str(debug_dir / f"login_test_fail_{ts}.png"))
        with open(debug_dir / f"login_test_fail_{ts}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return False


def save_cookies(driver, path: Path):
    cookies = driver.get_cookies()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    LOG.info("🍪 Cookies 已保存 => %s", path)


def load_cookies(driver, path: Path):
    if not path.exists():
        return False
    with path.open("r", encoding="utf-8") as f:
        cookies = json.load(f)
    driver.get("https://www.traceparts.cn/")  # 需先到根域
    for c in cookies:
        # selenium cookie dict 需包含 name/value
        driver.add_cookie({k: c[k] for k in ("name", "value", "domain", "path", "expiry", "secure", "httpOnly") if k in c})
    LOG.info("🍪 已加载 cookies")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TraceParts 登录示例")
    parser.add_argument("--email", default=os.getenv("TRACEPARTS_EMAIL"), help="邮箱")
    parser.add_argument("--password", default=os.getenv("TRACEPARTS_PASSWORD"), help="密码")
    parser.add_argument("--save", default="results/session_cookies.json", help="cookie 保存路径")
    parser.add_argument("--headful", action="store_true", help="显示浏览器窗口，便于调试")
    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error("需要提供 --email 和 --password，或设置环境变量 TRACEPARTS_EMAIL/PASSWORD")

    driver = build_driver(headful=args.headful)

    if login(driver, args.email, args.password):
        save_path = Path(args.save)
        save_cookies(driver, save_path)
        LOG.info("Cookies JSON 位置: %s (可用于后续脚本)", save_path.resolve())
        # 访问示例产品页
        driver.get(TEST_PRODUCT)
        time.sleep(3)
        LOG.info("示例产品页标题: %s", driver.title)
    driver.quit() 