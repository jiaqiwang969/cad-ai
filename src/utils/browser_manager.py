#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器管理器
===========
统一管理Chrome和Playwright浏览器实例
"""

import time
import random
import threading
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager
from queue import Queue, Empty
from config.settings import Settings
from config.logging_config import LoggerMixin

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.common.exceptions import WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Playwright imports
try:
    from playwright.sync_api import sync_playwright, Browser, Page, Playwright
    from playwright_stealth import stealth_sync
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BrowserPool:
    """浏览器实例池"""
    
    def __init__(self, max_size: int = 5, browser_type: str = 'selenium'):
        self.max_size = max_size
        self.browser_type = browser_type
        self._pool = Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._created_count = 0
    
    def get(self, timeout: float = 30) -> Any:
        """获取一个浏览器实例"""
        try:
            # 首先尝试从池中获取
            return self._pool.get(block=False)
        except Empty:
            # 池为空，检查是否可以创建新实例
            with self._lock:
                if self._created_count < self.max_size:
                    self._created_count += 1
                    return None  # 返回None表示需要创建新实例
            
            # 已达到最大实例数，等待可用实例
            try:
                return self._pool.get(timeout=timeout)
            except Empty:
                raise TimeoutError("无法获取浏览器实例")
    
    def put(self, browser: Any):
        """归还浏览器实例"""
        try:
            self._pool.put_nowait(browser)
        except:
            # 池已满，关闭浏览器
            with self._lock:
                self._created_count = max(0, self._created_count - 1)
            self._close_browser(browser)
    
    def _close_browser(self, browser: Any):
        """关闭浏览器"""
        try:
            if self.browser_type == 'selenium' and hasattr(browser, 'quit'):
                browser.quit()
            elif self.browser_type == 'playwright':
                if hasattr(browser, 'context'):
                    browser.context.close()
                elif hasattr(browser, 'close'):
                    browser.close()
        except:
            pass
    
    def clear(self):
        """清空池"""
        while not self._pool.empty():
            try:
                browser = self._pool.get_nowait()
                self._close_browser(browser)
            except Empty:
                break


class BrowserManager(LoggerMixin):
    """统一的浏览器管理器"""
    
    def __init__(self, browser_type: str = 'selenium', pool_size: int = 5):
        """
        初始化浏览器管理器
        
        Args:
            browser_type: 浏览器类型 ('selenium' 或 'playwright')
            pool_size: 浏览器池大小
        """
        self.browser_type = browser_type
        self.pool = BrowserPool(pool_size, browser_type)
        self._playwright = None
        self._browser = None
        
        # 检查可用性
        if browser_type == 'selenium' and not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium 未安装，请运行: pip install selenium")
        elif browser_type == 'playwright' and not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装，请运行: pip install playwright playwright-stealth")
    
    def _create_selenium_driver(self) -> webdriver.Chrome:
        """创建 Selenium Chrome 驱动"""
        options = ChromeOptions()
        
        # 基础选项
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # 反检测选项
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 固定用户代理 (优化: 使用固定User-Agent提升缓存效率)
        user_agent = Settings.get_user_agent(0)  # 使用第一个，保持一致性
        options.add_argument(f'--user-agent={user_agent}')
        
        # 隐身模式（可选）
        if Settings.CRAWLER.get('headless', True):
            options.add_argument('--headless')
        
        # 创建驱动
        driver = webdriver.Chrome(options=options)
        
        # 设置超时 (优化: 从90秒降到60秒，提升性能)
        driver.set_page_load_timeout(60)  # 固定60秒，与fast版本一致
        driver.implicitly_wait(10)
        
        # 执行反检测脚本
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.navigator.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
            '''
        })
        
        return driver
    
    def _create_playwright_browser(self) -> Page:
        """创建 Playwright 浏览器页面"""
        if not self._playwright:
            self._playwright = sync_playwright().start()
        
        if not self._browser:
            self._browser = self._playwright.chromium.launch(
                headless=Settings.CRAWLER.get('headless', True),
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
        
        # 创建新页面
        context = self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=Settings.get_user_agent(random.randint(0, 100)),
            locale='zh-CN',
        )
        
        page = context.new_page()
        
        # 应用隐身策略
        stealth_sync(page)
        
        # 设置超时
        page.set_default_timeout(Settings.CRAWLER['timeout'] * 1000)
        
        return page
    
    @contextmanager
    def get_browser(self):
        """
        获取浏览器实例的上下文管理器
        
        使用示例：
            with browser_manager.get_browser() as browser:
                # 使用 browser
                pass
        """
        browser = None
        need_close = False
        
        try:
            # 尝试从池中获取
            browser = self.pool.get(timeout=30)
            if browser is None:
                # 需要创建新实例
                self.logger.debug("创建新的浏览器实例")
                if self.browser_type == 'selenium':
                    browser = self._create_selenium_driver()
                else:
                    browser = self._create_playwright_browser()
            else:
                self.logger.debug("从池中获取浏览器实例")
            
            yield browser
            
        except Exception as e:
            self.logger.error(f"浏览器操作失败: {e}")
            need_close = True  # 出错时需要关闭浏览器
            raise
        finally:
            if browser:
                if need_close:
                    # 如果出错，关闭浏览器
                    self._close_browser(browser)
                else:
                    try:
                        # 简化浏览器清理 (优化: 减少清理开销，提升性能)
                        if self.browser_type == 'selenium':
                            try:
                                # 仅导航到空白页，减少清理开销
                                browser.get("about:blank")
                                # 跳过 cookies 和 storage 清理以提升性能
                                # 注意: 如果需要完全清理，可以在特定场景下启用
                            except Exception as e:
                                self.logger.debug(f"清理浏览器状态失败: {e}")
                                # 只有在浏览器真的无法使用时才关闭
                                try:
                                    browser.current_url  # 测试浏览器是否还活着
                                except:
                                    need_close = True
                        
                        if not need_close:
                            # 归还到池中
                            self.pool.put(browser)
                            self.logger.debug("浏览器实例已归还到池中")
                        else:
                            self._close_browser(browser)
                    except Exception as e:
                        # 如果归还失败，关闭浏览器
                        self.logger.warning(f"归还浏览器失败，将关闭: {e}")
                        self._close_browser(browser)
    
    def _close_browser(self, browser: Any):
        """关闭浏览器"""
        try:
            if self.browser_type == 'selenium':
                browser.quit()
            else:  # playwright
                if hasattr(browser, 'context'):
                    browser.context.close()
                else:
                    browser.close()
        except Exception as e:
            self.logger.error(f"关闭浏览器失败: {e}")
    
    def shutdown(self):
        """关闭管理器"""
        self.logger.info("关闭浏览器管理器")
        self.pool.clear()
        
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'browser_type': self.browser_type,
            'pool_size': self.pool.max_size,
            'created_count': self.pool._created_count,
            'available_count': self.pool._pool.qsize(),
        }


# 便捷函数
def create_browser_manager(browser_type: str = None, pool_size: int = None) -> BrowserManager:
    """创建浏览器管理器"""
    browser_type = browser_type or Settings.CRAWLER.get('browser_type', 'selenium')
    pool_size = pool_size or Settings.CRAWLER.get('browser_pool_size', 16)
    return BrowserManager(browser_type, pool_size) 