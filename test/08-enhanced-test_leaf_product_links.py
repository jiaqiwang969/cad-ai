#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 08 增强版 —— 使用playwright-stealth的叶节点产品链接提取
支持登录和Show More按钮点击
"""

import os
import re
import sys
import json
import time
import logging
from urllib.parse import urlparse, parse_qs
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import random

# 导入配置
from config.settings import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("test-08-enhanced")


class EnhancedProductLinkExtractor:
    """增强版产品链接提取器"""
    
    def __init__(self):
        self.auth_config = Settings.AUTH['accounts'][0]
        self.is_logged_in = False
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def _create_stealth_browser(self):
        """创建隐身浏览器"""
        self.playwright = sync_playwright().__enter__()
        
        self.browser = self.playwright.chromium.launch(
            headless=False,  # 有头模式，便于调试
            slow_mo=random.randint(100, 300),
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=VizDisplayCompositor',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--window-size=1920,1080',
                '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            ]
        )
        
        self.context = self.browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )
        
        self.page = self.context.new_page()
        stealth_sync(self.page)
        
        # 反检测脚本
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        LOG.info("✅ 隐身浏览器创建完成")
    
    def _human_like_delay(self, min_delay=0.5, max_delay=2.0):
        """人类行为延迟"""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def _stealth_login(self):
        """隐身登录"""
        if self.is_logged_in:
            return True
        
        try:
            LOG.info("🔐 开始隐身登录...")
            
            login_url = "https://www.traceparts.cn/en/sign-in"
            self.page.goto(login_url, wait_until="networkidle")
            self._human_like_delay(2, 4)
            
            # 输入邮箱
            LOG.info("📧 输入邮箱...")
            email_input = self.page.locator("input[type='email']")
            email_input.click()
            self._human_like_delay(0.3, 0.8)
            email_input.fill("")
            self._human_like_delay(0.2, 0.5)
            for char in self.auth_config['email']:
                email_input.type(char, delay=random.randint(50, 150))
            
            # 输入密码
            LOG.info("🔑 输入密码...")
            password_input = self.page.locator("input[type='password']")
            password_input.click()
            self._human_like_delay(0.3, 0.8)
            password_input.fill("")
            self._human_like_delay(0.2, 0.5)
            for char in self.auth_config['password']:
                password_input.type(char, delay=random.randint(50, 150))
            
            # 点击登录
            LOG.info("🚀 点击登录...")
            submit_btn = self.page.locator("button:has-text('Sign in')").first
            submit_btn.hover()
            self._human_like_delay(0.3, 0.8)
            submit_btn.click()
            
            # 等待登录响应
            self._human_like_delay(3, 6)
            
            # 检查是否成功
            current_url = self.page.url
            if "sign-in" not in current_url.lower():
                LOG.info("✅ 登录成功！")
                self.is_logged_in = True
                return True
            else:
                LOG.error("❌ 登录失败")
                return False
                
        except Exception as e:
            LOG.error(f"❌ 登录失败: {e}")
            return False
    
    def _scroll_and_click_show_more(self):
        """滚动并点击Show More按钮直到没有更多"""
        LOG.info("🔄 开始滚动和点击Show More...")
        
        click_count = 0
        max_clicks = 30  # 减少最大点击次数
        no_change_count = 0
        last_product_count = 0
        
        while click_count < max_clicks:
            # 滚动到底部
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)  # 减少等待时间
            
            # 检查当前产品数量
            current_products = len(self.page.query_selector_all("a[href*='&Product=']"))
            if current_products == last_product_count:
                no_change_count += 1
                if no_change_count >= 3:  # 连续3次没有变化就停止
                    LOG.info(f"📊 产品数量连续3次无变化 ({current_products}个)，停止点击")
                    break
            else:
                no_change_count = 0
                last_product_count = current_products
                LOG.info(f"📊 当前产品数量: {current_products}")
            
            # 查找Show More按钮
            show_more_clicked = False
            show_more_selectors = [
                'button:has-text("Show more")',
                'button:has-text("Show More")',
                'button:has-text("Show more results")',
                'button[class*="more-results"]',
                'button[class*="show-more"]'
            ]
            
            for selector in show_more_selectors:
                try:
                    buttons = self.page.query_selector_all(selector)
                    for button in buttons:
                        if button.is_visible() and button.is_enabled():
                            try:
                                button.scroll_into_view_if_needed()
                                time.sleep(0.3)
                                button.click()
                                click_count += 1
                                LOG.info(f"👆 已点击Show More按钮 (第{click_count}次)")
                                show_more_clicked = True
                                time.sleep(2)  # 减少等待时间
                                break
                            except Exception:
                                try:
                                    self.page.evaluate("button => button.click()", button)
                                    click_count += 1
                                    LOG.info(f"👆 通过JS点击Show More按钮 (第{click_count}次)")
                                    show_more_clicked = True
                                    time.sleep(2)
                                    break
                                except:
                                    continue
                    
                    if show_more_clicked:
                        break
                except Exception:
                    continue
            
            if not show_more_clicked:
                LOG.info("✅ 没有找到更多Show More按钮，加载完成")
                break
        
        if click_count >= max_clicks:
            LOG.warning(f"⚠️ 达到最大点击次数限制 ({max_clicks})")
        
        # 最后滚动到顶部
        self.page.evaluate("window.scrollTo(0, 0);")
        time.sleep(0.5)
    
    def extract_product_links(self, url: str) -> list:
        """提取产品链接"""
        try:
            # 创建浏览器
            self._create_stealth_browser()
            
            # 登录
            self._stealth_login()
            
            # 访问目标页面
            LOG.info(f"🌐 打开叶节点页面: {url}")
            self.page.goto(url, wait_until="networkidle")
            time.sleep(3)
            
            # 滚动并点击Show More
            self._scroll_and_click_show_more()
            
            # 提取所有产品链接
            LOG.info("📦 提取产品链接...")
            product_links = self.page.query_selector_all("a[href*='&Product=']")
            
            links = []
            seen = set()
            
            for link in product_links:
                href = link.get_attribute('href')
                if href and '/product/' in href and href not in seen:
                    seen.add(href)
                    links.append(href)
            
            LOG.info(f"🔗 共提取产品链接 {len(links)} 条")
            return links
            
        except Exception as e:
            LOG.error(f"提取产品链接失败: {e}")
            return []
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            LOG.warning(f"清理资源时出错: {e}")


def tp_code_from_url(url: str) -> str:
    """从 leaf URL 提取 TP 编码，例 TP01002002006"""
    qs_part = urlparse(url).query
    params = parse_qs(qs_part)
    cp = params.get('CatalogPath', [''])[0]
    if cp.startswith('TRACEPARTS:'):
        cp = cp.split(':', 1)[1]
    return cp


def main():
    # 读取命令行参数
    leaf_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-bearings-bearing-blocks-flanged-block-bearings?CatalogPath=TRACEPARTS%3ATP01002002002"

    tp_code = tp_code_from_url(leaf_url) or "UNKNOWN"
    
    # 创建增强版提取器
    extractor = EnhancedProductLinkExtractor()
    
    try:
        all_links = extractor.extract_product_links(leaf_url)
        
        if not all_links:
            LOG.warning("未抓取到任何产品链接！")
            return False
        
        # 输出到文件
        os.makedirs("results", exist_ok=True)
        out_file = f"results/product_links_enhanced_{tp_code}.json"
        
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump({
                "leaf_url": leaf_url, 
                "tp_code": tp_code, 
                "total": len(all_links), 
                "links": all_links,
                "method": "enhanced_playwright_stealth",
                "generated": time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)
        
        LOG.info(f"✅ 共抓取 {len(all_links)} 条产品链接，已保存到 {out_file}")
        return True
        
    except Exception as e:
        LOG.error(f"测试失败: {e}")
        return False


if __name__ == "__main__":
    success = main()
    print("✅ 增强版test-08成功" if success else "❌ 增强版test-08失败")