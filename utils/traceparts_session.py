#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TraceParts 会话管理工具

提供：
• build_driver(headless)
• load_cookies(driver, path)
• save_cookies(driver, path)
• ensure_login(driver, email, password, cookies_path) -> bool
  若 cookie 无效则自动登录并更新文件。
"""

import json
import time
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

LOGIN_URL = "https://www.traceparts.cn/en/login"
HOME_URL = "https://www.traceparts.cn/"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build_driver(headless: bool = True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1500,1000")
    return webdriver.Chrome(options=opts)


# ---------------------------------------------------------------------------
# Cookies helpers
# ---------------------------------------------------------------------------

def load_cookies(driver: "webdriver.Chrome", path: Path) -> bool:
    if not path.exists():
        return False
    try:
        cookies = json.load(path.open())
        driver.get(HOME_URL)
        for c in cookies:
            driver.add_cookie({k: c[k] for k in ("name", "value", "domain", "path", "expiry", "secure", "httpOnly") if k in c})
        return True
    except Exception:
        return False


def save_cookies(driver: "webdriver.Chrome", path: Path):
    cookies = driver.get_cookies()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Login logic
# ---------------------------------------------------------------------------

def _perform_login(driver: "webdriver.Chrome", email: str, password: str) -> bool:
    driver.get(LOGIN_URL)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
        driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys(email)
        driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
        # 点击按钮 （找 submit）
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        # 等待跳转回首页或产品页
        WebDriverWait(driver, 20).until(EC.url_changes(LOGIN_URL))
        time.sleep(2)
        return True
    except Exception:
        return False


def _is_logged_in(driver: "webdriver.Chrome") -> bool:
    # 简单规则：页面上不存在 Sign in 链接，或者存在用户头像
    try:
        driver.get(HOME_URL)
        time.sleep(2)
        # 若出现登录按钮
        sign_in = driver.find_elements(By.CSS_SELECTOR, "a[href*='login']:not([style*='display:none'])")
        return len(sign_in) == 0
    except Exception:
        return False


def ensure_login(driver: "webdriver.Chrome", *, email: str, password: str, cookies_path: Path) -> bool:
    """如果已登录返回 True，否则尝试加载 Cookie，如果还不行则自动登录。"""
    # 1) 先试试当前 driver
    if _is_logged_in(driver):
        return True
    # 2) 尝试加载 cookies
    if load_cookies(driver, cookies_path):
        if _is_logged_in(driver):
            return True
    # 3) 自动登录
    if not email or not password:
        return False
    ok = _perform_login(driver, email, password)
    if ok:
        save_cookies(driver, cookies_path)
    return ok 