#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反检测系统
========
动态伪装和反爬策略
"""

import random
import time
import logging
from typing import List, Dict, Any
from selenium.webdriver.chrome.options import Options


class AntiDetectionManager:
    """反检测管理器"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        
        # 扩展的User-Agent池
        self.user_agents = [
            # Windows Chrome
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            
            # Mac Chrome
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            
            # Linux Chrome
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            
            # Firefox
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
            
            # Edge
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        ]
        
        # 窗口尺寸池
        self.window_sizes = [
            (1920, 1080), (1366, 768), (1440, 900), (1536, 864),
            (1280, 720), (1600, 900), (1024, 768), (1680, 1050)
        ]
        
        # 请求间隔配置
        self.request_intervals = {
            'min_interval': 1.0,
            'max_interval': 4.0,
            'burst_threshold': 5,  # 连续请求阈值
            'burst_cooldown': 10.0  # 突发后冷却时间
        }
        
        # 请求计数器
        self.request_count = 0
        self.last_request_time = 0
        
        # 供应商特定策略
        self.vendor_strategies = {
            'industrietechnik': {
                'min_interval': 2.0,
                'max_interval': 5.0,
                'extra_headers': {
                    'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                }
            },
            'apostoli': {
                'min_interval': 1.0,
                'max_interval': 3.0,
                'extra_headers': {
                    'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
                }
            }
        }
    
    def get_optimized_chrome_options(self, vendor_hint: str = None) -> Options:
        """获取优化的Chrome选项"""
        options = Options()
        
        # 基础反检测设置
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        
        # 随机窗口尺寸
        width, height = random.choice(self.window_sizes)
        options.add_argument(f'--window-size={width},{height}')
        
        # 随机User-Agent
        user_agent = random.choice(self.user_agents)
        options.add_argument(f'--user-agent={user_agent}')
        
        # 禁用自动化标识
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 性能优化
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')  # 根据需要可以启用
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-extensions')
        
        # 内存优化
        options.add_argument('--memory-pressure-off')
        options.add_argument('--max_old_space_size=4096')
        
        # 网络优化
        options.add_argument('--aggressive-cache-discard')
        options.add_argument('--disable-background-timer-throttling')
        
        # 供应商特定优化
        if vendor_hint:
            self._apply_vendor_specific_options(options, vendor_hint)
        
        self.logger.debug(f"🎭 生成Chrome选项: UA={user_agent[:50]}..., 尺寸={width}x{height}")
        
        return options
    
    def _apply_vendor_specific_options(self, options: Options, vendor: str):
        """应用供应商特定选项"""
        if vendor == 'industrietechnik':
            # industrietechnik可能需要JavaScript
            # 移除禁用JavaScript的选项
            pass
        elif vendor == 'apostoli':
            # apostoli页面较简单，可以更激进的优化
            options.add_argument('--disable-css')
    
    def apply_request_throttling(self, vendor_hint: str = None):
        """应用请求限流"""
        current_time = time.time()
        
        # 获取间隔配置
        if vendor_hint and vendor_hint in self.vendor_strategies:
            strategy = self.vendor_strategies[vendor_hint]
            min_interval = strategy['min_interval']
            max_interval = strategy['max_interval']
        else:
            min_interval = self.request_intervals['min_interval']
            max_interval = self.request_intervals['max_interval']
        
        # 计算等待时间
        time_since_last = current_time - self.last_request_time
        random_interval = random.uniform(min_interval, max_interval)
        
        # 检查是否需要额外等待
        if time_since_last < random_interval:
            wait_time = random_interval - time_since_last
            self.logger.debug(f"⏳ 请求限流等待: {wait_time:.2f}s (vendor: {vendor_hint})")
            time.sleep(wait_time)
        
        # 检查突发请求
        self.request_count += 1
        if self.request_count % self.request_intervals['burst_threshold'] == 0:
            cooldown_time = self.request_intervals['burst_cooldown']
            self.logger.info(f"🧊 突发冷却: {cooldown_time}s (已处理 {self.request_count} 个请求)")
            time.sleep(cooldown_time)
        
        self.last_request_time = time.time()
    
    def setup_driver_stealth(self, driver):
        """设置driver隐身模式"""
        try:
            # 移除webdriver属性
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 伪造Chrome对象
            driver.execute_script("""
                Object.defineProperty(navigator, 'chrome', {
                    get: () => ({
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    }),
                });
            """)
            
            # 伪造权限API
            driver.execute_script("""
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: function() {
                            return Promise.resolve({ state: 'granted' });
                        },
                    }),
                });
            """)
            
            # 伪造插件信息
            driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => ([
                        { name: 'Chrome PDF Plugin', description: 'Portable Document Format' },
                        { name: 'Shockwave Flash', description: 'Shockwave Flash 32.0 r0' },
                    ]),
                });
            """)
            
            self.logger.debug("🥷 Driver隐身模式已设置")
            
        except Exception as e:
            self.logger.warning(f"⚠️ 隐身模式设置失败: {e}")
    
    def get_random_headers(self, vendor_hint: str = None) -> Dict[str, str]:
        """获取随机请求头"""
        base_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        # 添加供应商特定头部
        if vendor_hint and vendor_hint in self.vendor_strategies:
            extra_headers = self.vendor_strategies[vendor_hint].get('extra_headers', {})
            base_headers.update(extra_headers)
        
        return base_headers
    
    def detect_vendor_from_url(self, url: str) -> str:
        """从URL检测供应商"""
        url_lower = url.lower()
        
        # 检测已知的问题供应商
        if 'industrietechnik' in url_lower or 'item-industrietechnik' in url_lower:
            return 'industrietechnik'
        elif 'apostoli' in url_lower:
            return 'apostoli'
        
        # 检测其他常见供应商模式
        vendor_patterns = {
            'skf': ['skf'],
            'timken': ['timken'],
            'ntn': ['ntn'],
            'winco': ['winco', 'jw-winco'],
            'smc': ['smc'],
            'essentra': ['essentra'],
            'traceparts': ['traceparts-site'],
            'record': ['record-revolving']
        }
        
        for vendor, patterns in vendor_patterns.items():
            if any(pattern in url_lower for pattern in patterns):
                return vendor
        
        return 'generic'
    
    def simulate_human_behavior(self, driver):
        """模拟人类行为"""
        try:
            # 随机鼠标移动
            driver.execute_script("""
                var event = new MouseEvent('mousemove', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: Math.random() * window.innerWidth,
                    clientY: Math.random() * window.innerHeight
                });
                document.dispatchEvent(event);
            """)
            
            # 随机滚动
            scroll_amount = random.randint(100, 500)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.5, 1.5))
            
            # 回到顶部
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.3, 0.8))
            
            self.logger.debug("🤖 模拟人类行为完成")
            
        except Exception as e:
            self.logger.debug(f"人类行为模拟失败: {e}")
    
    def get_request_strategy(self, vendor_hint: str = None) -> Dict[str, Any]:
        """获取完整的请求策略"""
        return {
            'chrome_options': self.get_optimized_chrome_options(vendor_hint),
            'headers': self.get_random_headers(vendor_hint),
            'throttling_config': self.vendor_strategies.get(vendor_hint, self.request_intervals),
            'vendor': vendor_hint or 'generic'
        }