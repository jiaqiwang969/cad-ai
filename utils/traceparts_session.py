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
from datetime import datetime

# 优先尝试使用 undetected_chromedriver 以减少被反爬检测
try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# TraceParts 在不同地区域名可能返回 404；统一改用国际站 .com
LOGIN_URL = "https://www.traceparts.cn/en/sign-in"
HOME_URL = "https://www.traceparts.cn/"

# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def _build_chrome_options(headless: bool = True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1500,1000")
    # 反检测常用参数
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    # 常用 UA
    opts.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return opts


def build_driver(headless: bool = True):
    """构建 Selenium driver。若安装了 undetected_chromedriver 则优先使用。"""
    opts = _build_chrome_options(headless)

    if UC_AVAILABLE:
        try:
            driver = uc.Chrome(options=opts, headless=headless, use_subprocess=True)
            return driver
        except Exception:
            pass  # fallback

    return webdriver.Chrome(options=opts)


# ---------------------------------------------------------------------------
# Cookies helpers
# ---------------------------------------------------------------------------

def load_cookies(driver: "webdriver.Chrome", path: Path) -> bool:
    if not path.exists():
        return False
    try:
        cookies = json.load(path.open())
        if HOME_URL:
            driver.get(HOME_URL)
        else:
            driver.get("https://www.traceparts.cn/")
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
    # 若出现 404/403 可在此处加重试逻辑。但根据业务指定，只使用上述 URL。
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
    )

    try:
        # 聚合可能的 email/password 输入框选择器
        email_selector = "input[type='email'], input[name*='email' i], input[id*='email' i], input[placeholder*='email' i]"
        pwd_selector = "input[type='password'], input[name*='pass' i], input[id*='pass' i], input[placeholder*='password' i]"

        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, email_selector)))

        email_el = driver.find_element(By.CSS_SELECTOR, email_selector)
        pwd_el = driver.find_element(By.CSS_SELECTOR, pwd_selector)

        email_el.clear(); email_el.send_keys(email)
        pwd_el.clear(); pwd_el.send_keys(password)

        # 登录按钮：同时匹配 type submit 或文本包含 sign in / login
        btn_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button", "a", "input[type='button']"
        ]
        login_btn = None
        for sel in btn_selectors:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in elems:
                txt = (e.text or "").lower()
                if any(k in txt for k in ["sign in", "log in", "login", "sign-in"]):
                    login_btn = e; break
            if login_btn:
                break
        if not login_btn:
            # 退回使用第一个 submit
            login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        driver.execute_script("arguments[0].click();", login_btn)

        # 等待跳转回首页或产品页
        WebDriverWait(driver, 20).until(EC.url_changes(LOGIN_URL))
        time.sleep(2)
        return True
    except Exception:
        # 保存调试截图
        debug_dir = Path("results/login_debug")
        debug_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        driver.save_screenshot(str(debug_dir / f"login_fail_{ts}.png"))
        with open(debug_dir / f"login_fail_{ts}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return False


def _is_logged_in(driver: "webdriver.Chrome") -> bool:
    # 简单规则：页面上不存在 Sign in 链接，或者存在用户头像
    try:
        if not HOME_URL:
            driver.get("https://www.traceparts.cn/")
        else:
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