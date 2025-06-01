#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动登录 TraceParts 并保存会话 cookie
===================================
使用 Selenium 打开登录页，输入邮箱和密码，成功后将 Cookie 保存到
Settings.AUTH['session_file'] 指定的 JSON 文件。
"""

import sys
import os
import time
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config.settings import Settings


def save_session():
    email = Settings.AUTH['accounts'][0]['email']
    password = Settings.AUTH['accounts'][0]['password']
    session_file = Settings.AUTH['session_file']

    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,800')
    if Settings.CRAWLER.get('headless', True):
        options.add_argument('--headless')

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(90)

    try:
        print('🌐 打开登录页面...')
        driver.get(Settings.URLS['login'])

        # 接受 cookie banner（如果存在）
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'button#onetrust-accept-btn-handler'))
            )
            btn.click()
            time.sleep(0.5)
        except:
            pass

        print('✏️ 填写邮箱和密码...')
        email_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        pwd_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")

        email_input.clear(); email_input.send_keys(email)
        pwd_input.clear(); pwd_input.send_keys(password)

        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()

        print('⏳ 等待登录完成...')

        def logged_in(drv):
            # 成功条件 1：出现用户头像 / Sign out
            return drv.find_elements(By.CSS_SELECTOR, "a[href*='sign-out']") \
                or drv.find_elements(By.CSS_SELECTOR, "img[src*='avatar']")

        try:
            WebDriverWait(driver, 30).until(logged_in)
        except TimeoutException:
            # 仍在登录页，看看是不是验证码
            if "sign-in" in driver.current_url.lower():
                print("⚠️  可能出现验证码或额外验证，请手动处理，然后按回车继续...")
                input()
            else:
                pass   # 其他页面也算成功
        time.sleep(2)

        # 保存 cookies
        cookies = driver.get_cookies()
        os.makedirs(os.path.dirname(session_file), exist_ok=True)
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f'✅ 已保存 {len(cookies)} 条 cookie 到 {session_file}')

    finally:
        driver.quit()


if __name__ == '__main__':
    save_session() 