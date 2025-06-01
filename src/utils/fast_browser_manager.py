#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高性能浏览器管理器
================
专注性能的简化版浏览器管理器
"""

import time
import threading
from typing import Any
from contextlib import contextmanager
from queue import Queue, Empty

from config.settings import Settings
from config.logging_config import LoggerMixin

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.common.exceptions import WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class FastBrowserPool:
    """高性能浏览器池 (简化版)"""
    
    def __init__(self, max_size: int = 5):
        self.max_size = max_size
        self._pool = Queue(maxsize=max_size)
        self._lock = threading.Lock()
        self._created_count = 0
    
    def get(self, timeout: float = 30) -> Any:
        """获取一个浏览器实例"""
        try:
            return self._pool.get(block=False)
        except Empty:
            with self._lock:
                if self._created_count < self.max_size:
                    self._created_count += 1
                    return None
            
            try:
                return self._pool.get(timeout=timeout)
            except Empty:
                raise TimeoutError("无法获取浏览器实例")
    
    def put(self, browser: Any):
        """归还浏览器实例"""
        try:
            self._pool.put_nowait(browser)
        except:
            with self._lock:
                self._created_count = max(0, self._created_count - 1)
            self._close_browser(browser)
    
    def _close_browser(self, browser: Any):
        """关闭浏览器"""
        try:
            if hasattr(browser, 'quit'):
                browser.quit()
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


class FastBrowserManager(LoggerMixin):
    """高性能浏览器管理器"""
    
    def __init__(self, pool_size: int = 5):
        """
        初始化高性能浏览器管理器
        
        Args:
            pool_size: 浏览器池大小
        """
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium 未安装，请运行: pip install selenium")
        
        self.pool = FastBrowserPool(pool_size)
    
    def _create_fast_driver(self) -> webdriver.Chrome:
        """创建高性能 Chrome 驱动"""
        options = ChromeOptions()
        
        # 基础高性能选项
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # 固定用户代理 (利用缓存)
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 创建驱动
        driver = webdriver.Chrome(options=options)
        
        # 优化的超时设置
        driver.set_page_load_timeout(60)  # 60秒，与fast版本一致
        driver.implicitly_wait(5)  # 降低隐式等待
        
        return driver
    
    @contextmanager
    def get_browser(self):
        """
        获取浏览器实例的上下文管理器
        
        使用示例：
            with fast_browser_manager.get_browser() as browser:
                # 使用 browser
                pass
        """
        browser = None
        need_close = False
        
        try:
            browser = self.pool.get(timeout=30)
            if browser is None:
                self.logger.debug("创建新的高性能浏览器实例")
                browser = self._create_fast_driver()
            else:
                self.logger.debug("从池中获取浏览器实例")
            
            yield browser
            
        except Exception as e:
            self.logger.error(f"浏览器操作失败: {e}")
            need_close = True
            raise
        finally:
            if browser:
                if need_close:
                    self._close_browser(browser)
                else:
                    try:
                        # 最小化清理 (仅导航到空白页)
                        browser.get("about:blank")
                        self.pool.put(browser)
                        self.logger.debug("浏览器实例已归还到池中")
                    except Exception as e:
                        self.logger.warning(f"归还浏览器失败，将关闭: {e}")
                        self._close_browser(browser)
    
    def _close_browser(self, browser: Any):
        """关闭浏览器"""
        try:
            browser.quit()
        except Exception as e:
            self.logger.error(f"关闭浏览器失败: {e}")
    
    def shutdown(self):
        """关闭管理器"""
        self.logger.info("关闭高性能浏览器管理器")
        self.pool.clear()


# 便捷函数
def create_fast_browser_manager(pool_size: int = None) -> FastBrowserManager:
    """创建高性能浏览器管理器"""
    pool_size = pool_size or 5
    return FastBrowserManager(pool_size) 