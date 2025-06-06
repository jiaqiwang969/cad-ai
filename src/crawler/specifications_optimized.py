#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版产品规格爬取模块
====================
严格基于成功的测试脚本重写，确保完全一致
"""

import re
import time
import logging
import random
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class OptimizedSpecificationsCrawler:
    """优化版产品规格爬取器"""
    
    def __init__(self, log_level: int = logging.INFO):
        """初始化规格爬取器
        
        Args:
            log_level: 日志级别
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # 添加控制台处理器（如果还没有）
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
        
        # Selenium配置
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        
        # 随机化User-Agent避免被检测
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        self.chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        # 缓存已访问的URL，避免重复请求
        self.visited_urls = set()
        self.max_retries = 3
        self.retry_delay = 5
        
        # 性能监控
        self.stats = {
            'total_products': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_specifications': 0,
            'extraction_times': []
        }
        
        # 添加域名级弹窗处理缓存
        self._popup_handled_domains = set()
        
        # 优化后的等待时间配置
        self.page_load_wait = 1
        self.scroll_wait = 0.3
        self.popup_timeout = 3
        self.action_wait = 0.5
    
    def _create_optimized_driver(self):
        """创建优化的驱动（与测试脚本一致, 追加禁用图片）"""
        # 创建新的优化版 Options
        options = Options()
        
        # 基础设置
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # 随机化User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        options.add_argument('--disable-features=PaintHolding')  # 关闭首帧等待
        
        # 🔧 性能优化设置
        prefs = {
            "profile.managed_default_content_settings.images": 2,  # 禁用图片
            "profile.managed_default_content_settings.fonts": 2,    # 禁用字体
            "profile.managed_default_content_settings.stylesheets": 2,  # 禁用样式表
            "profile.managed_default_content_settings.media_stream": 2,  # 禁用媒体流
        }
        options.add_experimental_option("prefs", prefs)
        # 禁用自动化检测特征
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(5)
        driver.set_page_load_timeout(30)
        
        # 通过 CDP 屏蔽额外的静态资源
        try:
            driver.execute_cdp_cmd("Network.setBlockedURLs", {
                "urls": [
                    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.webp",
                    "*.woff*", "*.ttf", "*.otf", "*.eot",
                    "*googletagmanager*", "*google-analytics*", "*doubleclick*",
                    "*facebook*", "*twitter*", "*linkedin*"
                ]
            })
        except Exception as e:
            self.logger.debug(f"CDP命令失败（某些版本不支持）: {e}")
        
        return driver
    
    def _scroll_page_fully(self, driver):
        """完整滚动页面确保所有内容加载（更快）"""
        self.logger.debug("滚动页面确保内容完全加载...")
        for y in (driver.execute_script("return document.body.scrollHeight"), 0, driver.execute_script("return document.body.scrollHeight")//2):
            driver.execute_script("window.scrollTo(0, arguments[0]);", y)
            time.sleep(self.scroll_wait)
    
    def _set_items_per_page_to_all(self, driver) -> bool:
        """设置每页显示项目数为全部（基于 09-1 测试脚本）"""
        self.logger.debug("🔧 尝试设置每页显示项目数为全部...")
        
        # 首先检查是否存在分页控件
        try:
            pagination_indicators = [
                "//*[contains(text(), 'Items per page')]",
                "//*[contains(text(), 'items per page')]", 
                "//*[contains(text(), 'out of') and contains(text(), 'items')]",
                "//*[contains(text(), 'Show') and contains(text(), 'entries')]"
            ]
            
            has_pagination = False
            pagination_text = ""
            for selector in pagination_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements and any(elem.is_displayed() for elem in elements):
                        has_pagination = True
                        pagination_text = elements[0].text.strip()
                        self.logger.debug(f"✅ 检测到分页控件: '{pagination_text}'")
                        break
                except:
                    continue
            
            if not has_pagination:
                self.logger.debug("⚠️ 未检测到分页控件，可能是单页面，直接提取数据")
                return False
            else:
                self.logger.debug(f"📊 分页信息: {pagination_text}")
        except Exception as e:
            self.logger.warning(f"检测分页控件时出错: {e}")
            return False
        
        # 策略1: 寻找分页区域中的数字和下拉控件
        try:
            self.logger.debug("🔍 策略1: 查找分页区域的控件...")
            
            # 先查找包含"Items per page"的分页容器
            pagination_selectors = [
                "//*[contains(text(), 'Items per page')]",
                "//*[contains(text(), 'items per page')]",
                "//*[contains(text(), 'per page')]",
                "//*[contains(text(), 'out of') and contains(text(), 'items')]"
            ]
            
            pagination_container = None
            for selector in pagination_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        self.logger.debug(f"找到 {len(elements)} 个匹配的分页元素")
                        # 获取包含分页信息的最外层容器
                        for elem in elements:
                            # 查找父容器
                            for level in range(1, 4):  # 向上查找3层
                                try:
                                    container = elem.find_element(By.XPATH, f"./ancestor::*[{level}]")
                                    container_text = container.text.lower()
                                    if 'items per page' in container_text or 'out of' in container_text:
                                        pagination_container = container
                                        self.logger.debug(f"✅ 找到分页容器，文本: {container.text[:100]}...")
                                        break
                                except:
                                    continue
                            if pagination_container:
                                break
                    if pagination_container:
                        break
                except Exception as ex:
                    self.logger.debug(f"测试选择器 {selector} 失败: {ex}")
                    continue
            
            if pagination_container:
                # 在分页容器中查找所有可点击的数字
                self.logger.debug("🎯 在分页容器中查找可点击数字...")
                clickable_selectors = [
                    ".//select",
                    ".//button[text()]",
                    ".//a[text()]", 
                    ".//*[@role='button']",
                    ".//*[contains(@class,'select')]",
                    ".//*[contains(@class,'dropdown')]",
                    ".//*[contains(@onclick,'')]",
                    ".//*[text()='10']",
                    ".//*[text()='25']",
                    ".//*[text()='50']"
                ]
                
                found_elements_count = 0
                for selector in clickable_selectors:
                    try:
                        elements = pagination_container.find_elements(By.XPATH, selector)
                        if elements:
                            found_elements_count += len(elements)
                            self.logger.debug(f"选择器 '{selector}' 找到 {len(elements)} 个元素")
                        for elem in elements:
                            elem_text = elem.text.strip()
                            elem_tag = elem.tag_name
                            elem_class = elem.get_attribute('class') or ''
                            
                            self.logger.debug(f"🔍 找到可点击元素: {elem_tag} '{elem_text}' class='{elem_class[:50]}'")
                            
                            # 检查元素是否可见和可点击
                            is_displayed = elem.is_displayed() if hasattr(elem, 'is_displayed') else False
                            is_enabled = elem.is_enabled() if hasattr(elem, 'is_enabled') else False
                            self.logger.debug(f"   状态: 可见={is_displayed}, 可用={is_enabled}")
                            
                            # 如果是select，检查选项
                            if elem_tag == 'select':
                                options = elem.find_elements(By.TAG_NAME, 'option')
                                option_texts = [opt.text.strip() for opt in options]
                                self.logger.debug(f"📋 select选项: {option_texts}")
                                
                                # 查找All或大数字选项
                                for opt in options:
                                    text = opt.text.strip().lower()
                                    if text in ['all', '全部'] or (text.isdigit() and int(text) >= 50):
                                        self.logger.debug(f"🎯 尝试选择: '{opt.text}'")
                                        try:
                                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", opt)
                                            time.sleep(1)
                                            opt.click()
                                            # 等待页面刷新而非固定等待
                                            try:
                                                WebDriverWait(driver, 5).until(
                                                    lambda d: "All" in d.find_element(By.XPATH, "//button[text()='10' or text()='All']").text
                                                    or len(d.find_elements(By.TAG_NAME, 'tr')) > 15
                                                )
                                            except:
                                                time.sleep(2)
                                            self.logger.debug("✅ 成功选择All/大数字选项！")
                                            return True
                                        except Exception as click_error:
                                            self.logger.warning(f"❌ 点击选项失败: {click_error}")
                                            continue
                            
                            # 如果是数字文本且可点击，尝试点击
                            elif elem.is_displayed() and elem.is_enabled():
                                if elem_text.isdigit() or elem_text.lower() in ['all', '全部']:
                                    try:
                                        self.logger.debug(f"🖱️ 尝试点击数字/All元素: '{elem_text}'")
                                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                                        time.sleep(1)
                                        elem.click()
                                        time.sleep(3)
                                        
                                        # 查找弹出菜单中的All选项
                                        self.logger.debug("🔍 查找弹出菜单中的All选项...")
                                        all_found = False
                                        
                                        # 更全面的All选项查找
                                        all_selectors = [
                                            "//li[normalize-space(.)='All']",
                                            "//div[normalize-space(.)='All']",
                                            "//option[normalize-space(.)='All']",
                                            "//span[normalize-space(.)='All']",
                                            "//button[normalize-space(.)='All']",
                                            "//a[normalize-space(.)='All']",
                                            "//*[@role='option'][normalize-space(.)='All']",
                                            "//*[contains(@class,'option')][normalize-space(.)='All']",
                                            "//*[contains(@class,'menu-item')][normalize-space(.)='All']",
                                            "//li[text()='All']",
                                            "//li[normalize-space(.)='全部']"
                                        ]
                                        
                                        for all_sel in all_selectors:
                                            try:
                                                all_options = driver.find_elements(By.XPATH, all_sel)
                                                if all_options:
                                                    self.logger.debug(f"找到 {len(all_options)} 个All候选项 (选择器: {all_sel})")
                                                for all_option in all_options:
                                                    if all_option.is_displayed() and all_option.is_enabled():
                                                        self.logger.debug(f"🎯 找到可用All选项: '{all_option.text}' ({all_option.tag_name})")
                                                        # 先滚动到视图再点击
                                                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", all_option)
                                                        time.sleep(self.action_wait)
                                                        try:
                                                            all_option.click()
                                                        except Exception:
                                                            # 如果常规点击失败，尝试 JavaScript 点击
                                                            driver.execute_script("arguments[0].click();", all_option)
                                                        self.logger.debug("✅ 成功选择All选项！")
                                                        # 等待页面刷新而非固定等待
                                                        try:
                                                            WebDriverWait(driver, 5).until(
                                                                lambda d: "All" in d.find_element(By.XPATH, "//button[text()='10' or text()='All']").text
                                                                or len(d.find_elements(By.TAG_NAME, 'tr')) > 15
                                                            )
                                                        except:
                                                            time.sleep(2)
                                                        all_found = True
                                                        return True
                                            except Exception as e:
                                                self.logger.debug(f"测试All选择器失败: {e}")
                                                continue
                                        
                                        if not all_found:
                                            # 如果没找到All，尝试找最大数字
                                            self.logger.debug("⚠️ 未找到All，查找最大数字选项...")
                                            max_selectors = [
                                                "//li[text()='100']",
                                                "//li[text()='50']", 
                                                "//li[text()='25']",
                                                "//option[text()='100']",
                                                "//option[text()='50']"
                                            ]
                                            
                                            for max_sel in max_selectors:
                                                try:
                                                    max_options = driver.find_elements(By.XPATH, max_sel)
                                                    for max_option in max_options:
                                                        if max_option.is_displayed():
                                                            self.logger.debug(f"🔢 选择最大数字: {max_option.text}")
                                                            # 滚动到视图再点击
                                                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", max_option)
                                                            time.sleep(self.action_wait)
                                                            try:
                                                                max_option.click()
                                                            except Exception:
                                                                driver.execute_script("arguments[0].click();", max_option)
                                                            time.sleep(2)
                                                            return True
                                                except:
                                                    continue
                                            
                                            self.logger.debug("⚠️ 点击后未找到合适的选项")
                                        
                                    except Exception as e:
                                        self.logger.warning(f"❌ 点击失败: {e}")
                                        # 尝试 JavaScript 点击
                                        try:
                                            self.logger.debug(f"🔄 尝试JavaScript点击: '{elem_text}'")
                                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                                            time.sleep(self.action_wait)
                                            driver.execute_script("arguments[0].click();", elem)
                                            time.sleep(3)
                                            self.logger.debug("✅ JavaScript点击成功")
                                        except Exception as js_error:
                                            self.logger.debug(f"❌ JavaScript点击也失败: {js_error}")
                                        
                    except Exception as e:
                        self.logger.debug(f"查找元素失败: {e}")
                
                self.logger.debug(f"策略1总共找到 {found_elements_count} 个可能的分页元素")
                        
        except Exception as e:
            self.logger.warning(f"❌ 策略1失败: {e}")
        
        # 策略2: 更直接的查找方式
        try:
            self.logger.debug("策略2: 查找当前页数控件...")
            
            number_selectors = [
                "//select[option[text()='10']]",
                "//*[text()='10' and (@onclick or @role='button' or contains(@class,'select') or contains(@class,'dropdown'))]",
                "//button[text()='10']",
                "//a[text()='10']",
                "//*[@data-value='10']",
                "//*[contains(@class,'pagesize') or contains(@class,'page-size')]"
            ]
            
            for selector in number_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            elem_tag = elem.tag_name
                            elem_text = elem.text.strip()
                            elem_class = elem.get_attribute('class') or ''
                            
                            self.logger.debug(f"找到数字控件: {elem_tag} '{elem_text}' class='{elem_class}'")
                            
                            if elem_tag == 'select':
                                # 如果是select，查找All选项
                                options = elem.find_elements(By.TAG_NAME, 'option')
                                for opt in options:
                                    if opt.text.strip().lower() in ['all', '全部'] or (opt.text.strip().isdigit() and int(opt.text.strip()) >= 50):
                                        self.logger.debug(f"在select中选择: {opt.text}")
                                        # 滚动到视图再点击
                                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", opt)
                                        time.sleep(self.action_wait)
                                        try:
                                            opt.click()
                                        except Exception:
                                            driver.execute_script("arguments[0].click();", opt)
                                        time.sleep(2)
                                        return True
                            else:
                                # 如果是可点击元素，尝试点击
                                try:
                                    self.logger.debug(f"点击数字控件: {elem_text}")
                                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                                    time.sleep(1)
                                    try:
                                        elem.click()
                                    except Exception:
                                        driver.execute_script("arguments[0].click();", elem)
                                    time.sleep(3)
                                    
                                    # 查找弹出菜单中的All选项
                                    all_options = driver.find_elements(By.XPATH, "//li[normalize-space(.)='All'] | //option[normalize-space(.)='All'] | //*[@role='option'][normalize-space(.)='All']")
                                    for opt in all_options:
                                        if opt.is_displayed():
                                            # 滚动到视图再点击
                                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", opt)
                                            time.sleep(self.action_wait)
                                            try:
                                                opt.click()
                                            except Exception:
                                                driver.execute_script("arguments[0].click();", opt)
                                            self.logger.debug("选择了All选项")
                                            time.sleep(2)
                                            return True
                                            
                                except Exception as e:
                                    self.logger.debug(f"点击数字控件失败: {e}")
                                    
                except Exception as e:
                    self.logger.debug(f"查找数字控件失败: {e}")
                    
        except Exception as e:
            self.logger.debug(f"策略2失败: {e}")
        
        # 策略3: 查找所有select元素
        try:
            self.logger.debug("策略3: 检查所有select元素...")
            
            select_elements = driver.find_elements(By.TAG_NAME, 'select')
            self.logger.debug(f"页面共有 {len(select_elements)} 个select元素")
            
            for i, select_elem in enumerate(select_elements):
                try:
                    if not select_elem.is_displayed():
                        continue
                        
                    options = select_elem.find_elements(By.TAG_NAME, 'option')
                    option_data = []
                    has_numbers = False
                    
                    for opt in options:
                        text = opt.text.strip()
                        value = opt.get_attribute('value')
                        option_data.append(f"{text}({value})")
                        
                        # 检查是否有数字选项（分页相关）
                        if text.isdigit() and int(text) <= 100:
                            has_numbers = True
                    
                    self.logger.debug(f"Select {i+1}: 包含数字={has_numbers}")
                    if len(option_data) <= 10:  # 只显示选项少的select
                        self.logger.debug(f"选项: {option_data}")
                    
                    # 如果包含数字选项，可能是分页控件
                    if has_numbers:
                        self.logger.debug("这可能是分页控件，尝试选择最大值...")
                        
                        # 查找All或最大数字
                        best_option = None
                        for opt in options:
                            text = opt.text.strip().lower()
                            if text in ['all', '全部']:
                                best_option = opt
                                break
                            elif text.isdigit() and int(text) >= 50:
                                best_option = opt
                        
                        if best_option:
                            self.logger.debug(f"选择: {best_option.text}")
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", best_option)
                            time.sleep(1)
                            try:
                                best_option.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", best_option)
                            time.sleep(2)
                            return True
                            
                except Exception as e:
                    self.logger.debug(f"处理select {i+1}失败: {e}")
                    
        except Exception as e:
            self.logger.debug(f"策略3失败: {e}")
        
        self.logger.warning("❌ 所有策略都未能找到可用的分页控件")
        return False
    
    def _is_likely_product_reference(self, text: str) -> bool:
        """智能判断文本是否可能是产品编号（基于test-09-1）"""
        if not text or len(text) < 3:
            return False
        
        # 明显的排除项
        exclude_patterns = [
            r'^https?://',  # URL
            r'^www\.',      # 网址
            r'@',           # 邮箱
            r'^\d{4}-\d{2}-\d{2}',  # 日期格式
            r'^\+?\d{10,}$',  # 电话号码
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # 排除纯描述性文本（全是常见英文单词）
        common_words = [
            'description', 'manufacturer', 'material', 'color', 'size',
            'weight', 'length', 'width', 'height', 'diameter', 'thickness'
        ]
        
        text_lower = text.lower()
        if any(text_lower == word for word in common_words):
                return False
        
        # 积极的指标：包含这些特征的更可能是产品编号
        positive_indicators = 0
        
        # 1. 包含数字
        if any(c.isdigit() for c in text):
            positive_indicators += 2
        
        # 2. 包含连字符或下划线
        if '-' in text or '_' in text:
            positive_indicators += 1
        
        # 3. 包含大写字母（不是句子开头）
        if any(c.isupper() for c in text[1:]):
            positive_indicators += 1
        
        # 4. 长度适中（3-50个字符）
        if 3 <= len(text) <= 50:
            positive_indicators += 1
        
        # 5. 特殊格式模式
        special_patterns = [
            r'^\d+-\d+-\d+$',  # 5-14230-00
            r'^[A-Z]+\d+',     # SLS50, DIN787
            r'^\d+[A-Z]+',     # 14W, 230V
            r'^[A-Z0-9]+[-_][A-Z0-9]+',  # QAAMC10A050S
            r'^[A-Z]{2,}\d{2,}',  # DIN787, EN561
        ]
        
        for pattern in special_patterns:
            if re.match(pattern, text):
                positive_indicators += 2
                break
        
        # 如果积极指标足够多，认为是产品编号
        return positive_indicators >= 3
    
    def _is_valid_product_reference(self, text: str) -> bool:
        """判断文本是否是有效的产品编号（完全复制测试脚本并扩展）"""
        if not text or len(text) < 3:
            return False
        
        # 排除明显的产品描述
        if any(desc_word in text.lower() for desc_word in [
            'aluminum', 'extrusion', 'description', 'purchasing', 'links', 
            'manufacturer', 'jlcmc', 'product page', 'plastic', 'mounting',
            'angle', 'brackets', 'winco', 'type'
        ]):
            return False
        
        patterns = [
            r'^TXCE-[A-Z0-9]+-[0-9]+-[0-9]+-L[0-9]',  # TXCE系列
            r'^[A-Z]{2,4}-[0-9]',                      # 通用格式如 EN-561
            r'^[0-9]{3,}-[A-Z0-9]',                    # 数字开头格式
            r'^[A-Z][0-9]+[A-Z]*$',                    # 字母+数字格式
            r'^[A-Z]{2,}-[A-Z0-9]{2,}',               # 字母-字母数字格式
            r'^USC\d+T\d+$',                        # 🔧 新增NTN USC系列编号
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if any(c.isalpha() for c in text) and any(c.isdigit() for c in text) and len(text) <= 50:
                    return True
        return False
    
    def _extract_dimensions_from_cells(self, cells: List[str]) -> str:
        """从单元格中提取尺寸信息（复制测试脚本）"""
        for cell_text in cells:
            if not isinstance(cell_text, str): continue # 确保是字符串
            dimension_match = re.search(r'\b\d+([.,]\d+)?\s*[xX]\s*\d+([.,]\d+)?(\s*[xX]\s*\d+([.,]\d+)?)?\b', cell_text)
            if dimension_match:
                return dimension_match.group()
        return ''
    
    def _extract_weight_from_cells(self, cells: List[str]) -> str:
        """从单元格中提取重量或长度信息（复制测试脚本）"""
        for cell_text in cells:
            if not isinstance(cell_text, str): continue
            measure_match = re.search(r'(\d+[,.]\d+|\d+)\s*(kg|g|lbs|oz|mm|cm|m|inch|feet|ft|in)\b', cell_text.lower())
            if measure_match:
                return measure_match.group()
        return ''
    
    def _wait_for_content_loaded(self, driver, timeout=30):
        """等待页面内容完全加载 (来自修复脚本)"""
        self.logger.debug("⏳ 等待页面内容加载...")
        
        # 等待表格出现
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'table'))
            )
            self.logger.debug("✅ 表格元素已加载")
        except TimeoutException:
            self.logger.warning("⚠️ 等待超时，未检测到表格元素") # 更明确的日志
        
        # 额外等待动态内容
        self.logger.debug("额外等待5秒用于动态内容加载...")
        time.sleep(5)
        
        # 滚动页面确保内容完全展示
        self.logger.debug("滚动页面以确保内容完全展示...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

    def _get_cell_text_enhanced(self, cell_element):
        """增强版文本获取函数 (来自修复脚本)"""
        # 方法1: 标准 text 属性
        text = cell_element.text
        if text and text.strip():
            return text.strip()
        
        # 方法2: textContent 属性
        try:
            text = cell_element.get_attribute('textContent')
            if text and text.strip():
                return text.strip()
        except: # pylint: disable=bare-except
            pass # 忽略获取属性错误
        
        # 方法3: innerText 属性
        try:
            text = cell_element.get_attribute('innerText')
            if text and text.strip():
                return text.strip()
        except: # pylint: disable=bare-except
            pass
        
        # 方法4: innerHTML 并提取纯文本
        try:
            html = cell_element.get_attribute('innerHTML')
            if html:
                text = re.sub(r'<[^>]+>', '', html).strip()
                if text:
                    return text
        except: # pylint: disable=bare-except
            pass
        
        # 方法5: 子元素文本 (简化版，避免递归过深)
        try:
            child_texts = []
            # 直接获取所有子孙节点的文本内容，WebDriver会自动处理
            all_text_nodes = cell_element.find_elements(By.XPATH, ".//text()[normalize-space()]")
            for node in all_text_nodes:
                # Selenium WebDriver find_elements by XPATH with text() might return WebElements
                # representing text nodes. Their .text attribute should give the text.
                # However, a more robust way if 'node' is a text node is to get its 'textContent'
                # This part needs careful testing with Selenium's behavior for XPATH text() nodes.
                # For simplicity and robustness with Selenium, prefer higher-level text attributes if possible.
                # The initial .text or .get_attribute('textContent') on the cell_element should be prioritized.
                # This path is a deeper fallback.
                # A simpler approach for children if the above failed:
                children = cell_element.find_elements(By.XPATH, "./*")
                if children: # Only if direct children exist
                    temp_text = ' '.join(child.text.strip() for child in children if child.text and child.text.strip())
                    if temp_text:
                         child_texts.append(temp_text)

            if child_texts:
                full_child_text = ' '.join(child_texts).strip()
                if full_child_text:
                    return full_child_text
        except: # pylint: disable=bare-except
            pass
        
        return ''

    def _find_all_tables_enhanced(self, driver):
        """增强版表格查找 (来自修复脚本)"""
        self.logger.debug("🔍 查找页面中的所有表格...")
        tables_info = []
        
        try:
            tables = driver.find_elements(By.TAG_NAME, 'table')
        except Exception as e:
            self.logger.error(f"查找表格元素时发生错误: {e}")
            return tables_info
            
        self.logger.info(f"📊 找到 {len(tables)} 个表格")
        
        for i, table in enumerate(tables):
            try:
                if not table.is_displayed(): # 跳过不可见的表格
                    self.logger.debug(f"  表格 {i+1} 不可见，已跳过。")
                    continue

                rows = table.find_elements(By.TAG_NAME, 'tr')
                if not rows:
                    self.logger.debug(f"  表格 {i+1} 没有行，已跳过。")
                    continue
                    
                non_empty_rows = 0
                total_cells = 0
                sample_texts = []
                
                for row_idx, row in enumerate(rows[:5]): # 只检查前5行
                    try:
                        cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                        if cells:
                            total_cells += len(cells)
                            row_texts = []
                            for cell_idx, cell in enumerate(cells[:5]): # 每行只检查前5个单元格
                                cell_text = self._get_cell_text_enhanced(cell)
                                if cell_text:
                                    row_texts.append(cell_text)
                            
                            if row_texts:
                                non_empty_rows += 1
                                sample_texts.extend(row_texts) 
                    except Exception as e_cell:
                        self.logger.debug(f"表格 {i+1} 行 {row_idx+1} 单元格处理失败: {e_cell}")

                table_info = {
                    'index': i,
                    'rows_count': len(rows),
                    'non_empty_rows': non_empty_rows,
                    'total_cells': total_cells, # 实际检查的单元格数
                    'sample_texts': list(set(sample_texts))[:10], # 去重并取最多10个样本
                    'element': table
                }
                tables_info.append(table_info)
                self.logger.info(f"  表格 {i+1}: {len(rows)} 行, {non_empty_rows}有效行 (前5行样本), 样本: {table_info['sample_texts']}")
            except Exception as e_table:
                self.logger.warning(f"  表格 {i+1} 分析失败: {e_table}")
        
        return tables_info

    def _is_likely_product_reference_enhanced(self, text: str) -> bool:
        """增强版产品编号判断 (采用test-09-1成功逻辑)"""
        if not text or len(text) < 3: # 太短的文本不太可能是编号
            return False
        
        text = str(text) # 确保是字符串

        # 明显的排除项 (简化版，与test-09-1保持一致)
        exclude_patterns = [
            r'^https?://',  # URL
            r'^www\.',      # 网址
            r'@',           # 邮箱
            r'^\d{4}-\d{2}-\d{2}',  # 日期格式
            r'^\+?\d{10,}$',  # 电话号码
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.debug(f"'{text}' 被排除 (规则: {pattern})")
                return False
        
        # 排除纯描述性文本（与test-09-1保持一致的简化版本）
        common_words = [
            'description', 'manufacturer', 'material', 'color', 'size',
            'weight', 'length', 'width', 'height', 'diameter', 'thickness'
        ]
        
        text_lower = text.lower()
        if any(text_lower == word for word in common_words):
            self.logger.debug(f"'{text}' 被排除 (常见描述词)")
            return False
        
        # 积极的指标：包含这些特征的更可能是产品编号 (与test-09-1保持一致)
        positive_indicators = 0
        
        # 1. 包含数字
        if any(c.isdigit() for c in text):
            positive_indicators += 2
        
        # 2. 包含连字符或下划线
        if '-' in text or '_' in text:
            positive_indicators += 1
        
        # 3. 包含大写字母（不是句子开头）
        if any(c.isupper() for c in text[1:]):
            positive_indicators += 1
        
        # 4. 长度适中（3-50个字符）
        if 3 <= len(text) <= 50:
            positive_indicators += 1
        
        # 5. 特殊格式模式 (与test-09-1保持一致)
        special_patterns = [
            r'^\d+-\d+-\d+$',  # 5-14230-00
            r'^[A-Z]+\d+',     # SLS50, DIN787
            r'^\d+[A-Z]+',     # 14W, 230V
            r'^[A-Z0-9]+[-_][A-Z0-9]+',  # QAAMC10A050S
            r'^[A-Z]{2,}\d{2,}',  # DIN787, EN561
            r'^USC\d+T\d+$',   # USC201T20, USC202T20等NTN产品编号
        ]
        
        for pattern in special_patterns:
            if re.match(pattern, text):
                positive_indicators += 2
                self.logger.debug(f"'{text}' 匹配特殊格式模式: {pattern}")
                break

        self.logger.debug(f"'{text}' 的最终产品编号评分为: {positive_indicators}")
        return positive_indicators >= 3  # 使用test-09-1的成功阈值

    def _extract_all_specifications(self, driver) -> List[Dict[str, Any]]:
        """提取所有产品规格——复刻 test/09-1 的完整逻辑"""
        self.logger.debug("开始提取所有产品规格...")
        
        specifications = []
        seen_references = set()
        
        try:
            # 等待页面稳定
            time.sleep(self.page_load_wait)
            
            # 弹窗处理（同test/09-1）
            current_domain = driver.current_url.split('/')[2]
            if current_domain not in self._popup_handled_domains:
                self.logger.debug("检测并处理许可协议弹窗...")
                
                # 查找弹窗
                popup_selectors = [
                    "//*[contains(@class, 'modal')]",
                    "//*[contains(@class, 'popup')]",
                    "//*[contains(@class, 'dialog')]",
                    "//*[contains(@class, 'overlay')]"
                ]
                
                popup_found = False
                for selector in popup_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                popup_found = True
                                break
                        if popup_found:
                            break
                    except:
                        continue
                
                if popup_found:
                    # 简化的确认按钮文本列表
                    confirm_texts = [
                        'i understand and accept',
                        'accept', 'agree', 'continue', 'ok'
                    ]
                    
                    confirm_clicked = False
                    for text in confirm_texts:
                        if confirm_clicked:
                            break
                        
                        button_selectors = [
                            f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')]",
                            f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')]"
                        ]
                        
                        for selector in button_selectors:
                            try:
                                buttons = driver.find_elements(By.XPATH, selector)
                                for button in buttons:
                                    if button.is_displayed() and button.is_enabled():
                                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
                                        time.sleep(self.action_wait)
                                        button.click()
                                        confirm_clicked = True
                                        self._popup_handled_domains.add(current_domain)
                                        
                                        # 动态等待弹窗消失
                                        try:
                                            WebDriverWait(driver, 3).until(
                                                lambda d: not button.is_displayed()
                                            )
                                        except:
                                            time.sleep(self.action_wait)
                                        
                                        break
                            except:
                                continue
            
            # 滚动页面
            self._scroll_page_fully(driver)
            
            # 获取所有表格
            all_tables = driver.find_elements(By.TAG_NAME, 'table')
            
            # 查找产品表格（采用test-09-1的完整逻辑）
            product_section_keywords = [
                'product selection', 'product list', 'product specifications',
                'available products', 'product variants', 'models available',
                'produktauswahl', 'produktliste', 'produktspezifikationen',  # 德语
                'sélection de produits', 'liste des produits',  # 法语
                '产品选择', '产品列表', '产品规格',  # 中文
                'specification', 'specifications', 'technical data'
            ]
            table_element = None
            
            # 1. 通过标题查找（采用test-09-1的详细逻辑）
            for keyword in product_section_keywords:
                xpath_selectors = [
                    f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                    f"//h1[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                    f"//h2[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                    f"//h3[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]"
                ]
                
                for selector in xpath_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.text.strip():
                                # 查找该元素附近的表格
                                try:
                                    parent = elem.find_element(By.XPATH, "./..")
                                    tables_in_parent = parent.find_elements(By.TAG_NAME, 'table')
                                    
                                    if not tables_in_parent:
                                        tables_in_parent = elem.find_elements(By.XPATH, "./following-sibling::*//table")
                                    
                                    if not tables_in_parent:
                                        tables_in_parent = elem.find_elements(By.XPATH, "./following::table")
                                    
                                    if tables_in_parent:
                                        candidate_table = tables_in_parent[0]
                                        candidate_rows = candidate_table.find_elements(By.TAG_NAME, 'tr')
                                        
                                        # 检查表格是否包含有意义数据
                                        has_meaningful_data = False
                                        for row in candidate_rows[:3]:
                                            cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                                            cell_texts = [cell.text.strip() for cell in cells]
                                            non_empty_cells = [text for text in cell_texts if text and len(text) > 1]
                                            if len(non_empty_cells) >= 2:
                                                has_meaningful_data = True
                                                break
                                        
                                        if has_meaningful_data:
                                            table_element = candidate_table
                                            break
                                except:
                                    continue
                        if table_element:
                            break
                    except:
                        continue
                if table_element:
                    break
            
            # 2. 如果没找到，使用test-09-1的表格评分系统
            if not table_element:
                self.logger.debug("未通过标题找到表格，使用评分系统选择最佳表格...")
                visible_tables = [t for t in all_tables if t.is_displayed()]
                
                if visible_tables:
                    best_table = None
                    best_score = 0
                    
                    for i, table in enumerate(visible_tables):
                        rows = table.find_elements(By.TAG_NAME, 'tr')
                        score = 0
                        non_empty_rows = 0
                        
                        for j, row in enumerate(rows[:10]):  # 只检查前10行
                            cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                            cell_texts = [cell.text.strip() for cell in cells]
                            non_empty_cells = [text for text in cell_texts if text and len(text) > 1]
                            
                            if len(non_empty_cells) >= 2:
                                non_empty_rows += 1
                                score += len(non_empty_cells)
                                
                                # 检查是否包含产品编号相关词汇
                                for text in cell_texts:
                                    text_lower = text.lower()
                                    if any(keyword in text_lower for keyword in ['part', 'number', 'model', 'reference', 'item']):
                                        score += 10
                                    # 检查是否看起来像产品编号
                                    if self._is_likely_product_reference_enhanced(text):
                                        score += 5
                        
                        if score > best_score:
                            best_score = score
                            best_table = table
                    
                    table_element = best_table
            
            if not table_element:
                self.logger.warning("未找到产品表格")
                return specifications

            rows = table_element.find_elements(By.TAG_NAME, 'tr')
            # 判断纵向/横向
            two_col = 0
            for r in rows[:5]:
                if len(r.find_elements(By.CSS_SELECTOR, 'td, th')) == 2:
                    two_col += 1
            is_vertical = two_col >= 3

            # 3️⃣ 纵向表格处理
            if is_vertical:
                for idx, r in enumerate(rows):
                    cells = r.find_elements(By.CSS_SELECTOR, 'td, th')
                    if len(cells) != 2:
                        continue
                    prop_name = self._get_cell_text_enhanced(cells[0])
                    prop_val = self._get_cell_text_enhanced(cells[1])
                    if prop_val and prop_val not in seen_references and self._is_likely_product_reference_enhanced(prop_val):
                        spec = {
                            'reference': prop_val,
                            'row_index': idx,
                            'property_name': prop_name,
                            'dimensions': self._extract_dimensions_from_cells([prop_val]),
                            'weight': self._extract_weight_from_cells([prop_val]),
                            'table_type': 'vertical'
                        }
                        specifications.append(spec)
                        seen_references.add(prop_val)
            else:
                #  横向表头定位
                header_idx = -1
                header_cells_text = []
                for i, r in enumerate(rows):
                    cells = r.find_elements(By.CSS_SELECTOR, 'td, th')
                    th_cells = r.find_elements(By.TAG_NAME, 'th')
                    if len(th_cells) == len(cells) and len(cells) > 0:
                        header_idx = i
                        header_cells_text = [self._get_cell_text_enhanced(c) for c in cells]
                        break
                product_cols = []
                if header_cells_text:
                    for j, h in enumerate(header_cells_text):
                        h_l = h.lower()
                        matching_keywords = []
                        for kw in [
                            'part number','part no','part#','p/n','product number','product code','model',
                            'reference', 'ref', 'item number', 'item no',
                            'catalog number', 'cat no', 'sku',
                            'description',  # 包含description作为可能的产品编号列（与test-09-1一致）
                            'bestellnummer', 'artikelnummer', 'teilenummer',  # 德语
                            'numéro', 'référence',  # 法语
                            'número', 'codigo',  # 西班牙语
                            '型号', '编号', '料号'  # 中文
                        ]:
                            if kw in h_l:
                                matching_keywords.append(kw)
                        
                        if matching_keywords:
                            product_cols.append(j)
                            self.logger.debug(f"识别产品编号列 {j+1}: '{h}' (匹配: {matching_keywords})")
                    
                    # 通用简化逻辑：只使用第一个产品编号列（与test-09-1一致）
                    if len(product_cols) > 1:
                        self.logger.debug(f"发现 {len(product_cols)} 个产品编号列，只使用第一个主要列")
                        product_cols = product_cols[:1]
                
                # 如果没有识别到产品编号列，使用智能判断（与test-09-1一致）
                if not product_cols:
                    self.logger.debug("未识别到明确的产品编号列，将使用智能判断")
                    use_smart = True
                else:
                    use_smart = False

                for i, r in enumerate(rows):
                    if i <= header_idx:
                        continue
                    cells = r.find_elements(By.CSS_SELECTOR, 'td, th')
                    cell_texts = [self._get_cell_text_enhanced(c) for c in cells]
                    if not cell_texts:
                        continue
                    found_in_row = False
                    if use_smart:
                        # 智能检测模式：扫描所有单元格（与test-09-1完全一致）
                        for j, cell_text in enumerate(cell_texts):
                            if cell_text and len(cell_text) >= 3 and cell_text not in seen_references:
                                if self._is_likely_product_reference_enhanced(cell_text):
                                    column_name = header_cells_text[j] if header_cells_text and j < len(header_cells_text) else f"列{j+1}"
                                    self.logger.debug(f"在 {column_name} 中发现产品编号: '{cell_text}'")
                                    
                                    spec = {
                                        'reference': cell_text,
                                        'row_index': i,
                                        'column_index': j,
                                        'column_name': column_name,
                                        'dimensions': self._extract_dimensions_from_cells(cell_texts),
                                        'weight': self._extract_weight_from_cells(cell_texts),
                                        'all_cells': cell_texts,  # 添加所有单元格信息（与test-09-1一致）
                                        'table_type': 'horizontal'
                                    }
                                    specifications.append(spec)
                                    seen_references.add(cell_text)
                                    found_in_row = True
                                    # 在智能模式下，每行只取第一个符合条件的（与test-09-1一致）
                                    break
                    else:
                        # 使用识别的产品编号列（与test-09-1一致）
                        for col_idx in product_cols:
                            if col_idx < len(cell_texts):
                                cell_text = cell_texts[col_idx]
                                
                                if cell_text and len(cell_text) >= 3 and cell_text not in seen_references:
                                    # 对产品编号列的内容，放宽验证（与test-09-1一致）
                                    if cell_text and cell_text.lower() not in ['', 'n/a', 'na', '-', '/', 'none']:
                                        column_name = header_cells_text[col_idx] if col_idx < len(header_cells_text) else f"列{col_idx+1}"
                                        
                                        spec = {
                                            'reference': cell_text,
                                            'row_index': i,
                                            'column_index': col_idx,
                                            'column_name': column_name,
                                            'dimensions': self._extract_dimensions_from_cells(cell_texts),
                                            'weight': self._extract_weight_from_cells(cell_texts),
                                            'all_cells': cell_texts,  # 添加所有单元格信息（与test-09-1一致）
                                            'table_type': 'horizontal'
                                        }
                                        specifications.append(spec)
                                        seen_references.add(cell_text)
                                        found_in_row = True
                                        break
            return specifications
        except Exception as e:
            self.logger.error(f"提取规格时发生异常: {e}")
            return specifications

    def _close_disclaimer_popup(self, driver, timeout: int = 10) -> bool:
        """检测并关闭免责声明/许可协议弹窗（基于 09-1 测试脚本）"""
        # 检查域名是否已处理
        try:
            current_domain = driver.current_url.split('/')[2]
            if current_domain in self._popup_handled_domains:
                self.logger.debug(f"[POPUP] 跳过已处理域名: {current_domain}")
                return False
        except Exception:
            current_domain = None
        
        self.logger.debug("[POPUP] 检测免责声明弹窗...")
        
        # 使用更短的超时时间
        actual_timeout = self.popup_timeout
        
        # 🔧 查找可能的弹窗和确认按钮（基于 09-1）
        popup_selectors = [
            # 通用弹窗容器
            "//*[contains(@class, 'modal')]",
            "//*[contains(@class, 'popup')]", 
            "//*[contains(@class, 'dialog')]",
            "//*[contains(@class, 'overlay')]",
            # 包含许可、条款、免责声明等文本的元素
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'disclaimer')]",
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'liability')]",
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'terms')]",
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'license')]",
            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]"
        ]
        
        popup_found = False
        for selector in popup_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        popup_text = elem.text.strip()[:100] + "..." if len(elem.text.strip()) > 100 else elem.text.strip()
                        self.logger.debug(f"[POPUP] 发现弹窗元素: '{popup_text}'")
                        popup_found = True
                        break
                if popup_found:
                    break
            except Exception:
                continue
        
        if not popup_found:
            self.logger.debug("[POPUP] 未检测到弹窗")
            if current_domain:
                self._popup_handled_domains.add(current_domain)
            return False
        
        self.logger.debug("[POPUP] 检测到弹窗，查找确认按钮...")
        
        # 查找确认按钮的多种可能文本（基于 09-1）
        confirm_button_texts = [
            # 英文
            'i understand and accept',
            'i understand', 
            'accept',
            'agree',
            'continue', 
            'ok'
        ]
        
        confirm_clicked = False
        
        for button_text in confirm_button_texts:
            if confirm_clicked:
                break
                
            self.logger.debug(f"[POPUP] 搜索确认按钮: '{button_text}'")
            
            # 多种按钮选择器（基于 09-1）
            button_selectors = [
                f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{button_text}')]",
                f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{button_text}')]",
                f"//input[@type='button'][contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{button_text}')]",
                f"//input[@type='submit'][contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{button_text}')]",
                f"//*[@role='button'][contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{button_text}')]",
                f"//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{button_text}') and (@onclick or contains(@class, 'button') or contains(@class, 'btn'))]"
            ]
            
            for selector in button_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_full_text = button.text.strip()
                            self.logger.debug(f"[POPUP] 找到确认按钮: '{button_full_text}'")
                            
                            # 尝试点击按钮（基于 09-1 策略）
                            try:
                                # 滚动到按钮位置
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
                                time.sleep(self.action_wait)
                                
                                # 点击按钮
                                button.click()
                                self.logger.debug(f"[POPUP] ✅ 成功点击确认按钮!")
                                confirm_clicked = True
                                
                                # 等待弹窗消失（使用显式等待）
                                try:
                                    WebDriverWait(driver, 3).until(lambda d: not button.is_displayed())
                                except Exception:
                                    time.sleep(self.action_wait)
                                
                                # 记录已处理
                                if current_domain:
                                    self._popup_handled_domains.add(current_domain)
                                
                                # 检查弹窗是否消失
                                try:
                                    if not button.is_displayed():
                                        self.logger.debug("[POPUP] ✅ 弹窗已消失")
                                    else:
                                        self.logger.debug("[POPUP] ⚠️ 弹窗可能仍然存在")
                                except:
                                    self.logger.debug("[POPUP] ✅ 按钮元素已移除，弹窗应已关闭")
                                
                                return True
                                
                            except Exception as e:
                                self.logger.debug(f"[POPUP] ❌ 点击按钮失败: {e}")
                                # 尝试JavaScript点击（基于 09-1）
                                try:
                                    driver.execute_script("arguments[0].click();", button)
                                    self.logger.debug(f"[POPUP] ✅ JavaScript点击成功!")
                                    confirm_clicked = True
                                    time.sleep(3)
                                    if current_domain:
                                        self._popup_handled_domains.add(current_domain)
                                    return True
                                except Exception as e2:
                                    self.logger.debug(f"[POPUP] ❌ JavaScript点击也失败: {e2}")
                    
                    if confirm_clicked:
                        break
                        
                except Exception:
                    continue
        
        if not confirm_clicked:
            self.logger.debug("[POPUP] ⚠️ 未找到可点击的确认按钮，尝试通用方法...")
            
            # 最后尝试：查找所有可见的按钮并尝试点击（基于 09-1）
            try:
                all_buttons = driver.find_elements(By.CSS_SELECTOR, "button, input[type='button'], input[type='submit'], a[role='button'], .btn, .button")
                for button in all_buttons:
                    if button.is_displayed() and button.is_enabled():
                        button_text = button.text.strip().lower()
                        button_value = (button.get_attribute('value') or '').strip().lower()
                        
                        # 检查是否包含确认相关的关键词
                        confirm_keywords = ['accept', 'agree', 'understand', 'continue', 'ok', 'confirm', 'proceed']
                        if any(keyword in button_text or keyword in button_value for keyword in confirm_keywords):
                            self.logger.debug(f"[POPUP] 尝试通用按钮: '{button.text.strip()}'")
                            try:
                                # 先滚动再点击
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
                                time.sleep(self.action_wait)
                                button.click()
                                self.logger.debug(f"[POPUP] ✅ 通用按钮点击成功!")
                                time.sleep(3)
                                if current_domain:
                                    self._popup_handled_domains.add(current_domain)
                                return True
                            except:
                                # 尝试 JavaScript 点击
                                try:
                                    driver.execute_script("arguments[0].click();", button)
                                    self.logger.debug(f"[POPUP] ✅ 通用按钮JavaScript点击成功!")
                                    time.sleep(3)
                                    if current_domain:
                                        self._popup_handled_domains.add(current_domain)
                                    return True
                                except:
                                    continue
            except Exception as e:
                self.logger.debug(f"[POPUP] 通用方法失败: {e}")
        
        self.logger.warning("[POPUP] ❌ 无法处理免责声明弹窗")
        return False

    def _extract_specifications_with_driver(self, driver, product_url: str) -> List[Dict[str, Any]]:
        """在已存在 driver 的情况下提取规格，用于 driver 复用池"""
        try:
            self.logger.debug(f"[POOL] get {product_url}")
            driver.get(product_url)
            time.sleep(2)
            self._close_disclaimer_popup(driver)
            self._set_items_per_page_to_all(driver)
            self._scroll_page_fully(driver)
            return self._extract_all_specifications(driver)
        except Exception as e:
            self.logger.error(f"[POOL] 提取失败: {e}")
            return []

    def extract_batch_specifications(self, product_urls: List[str], max_workers: int = None) -> Dict[str, Any]:
        """批量提取产品规格（优化版）——使用持久化的driver池
        
        Args:
            product_urls: 产品URL列表
            max_workers: 最大并发数，默认根据URL数量动态调整
        
        Returns:
            包含所有提取结果的字典
        """
        if not product_urls:
            return {'results': [], 'summary': {}}
        
        # 动态调整线程数
        if max_workers is None:
            # 快速模式下使用更多线程
            max_workers = min(len(product_urls), 12)  # 最多12个线程
            # 确保至少有2个线程
            max_workers = max(max_workers, 2)
        
        self.logger.info(f"📦 开始批量提取 {len(product_urls)} 个产品的规格")
        self.logger.info(f"   使用 {max_workers} 个并发线程")
        
        start_time = time.time()
        results = []
        
        # 创建线程本地存储，每个线程维护自己的driver
        import threading
        thread_local = threading.local()
        
        def get_thread_driver():
            """获取当前线程的driver，如果不存在则创建"""
            if not hasattr(thread_local, 'driver'):
                thread_local.driver = self._create_optimized_driver()
            return thread_local.driver
        
        def process_url_batch(url_batch):
            """处理一批URL（同一个线程内串行处理）"""
            batch_results = []
            driver = get_thread_driver()
            
            for url in url_batch:
                try:
                    specs = self._extract_specifications_with_driver(driver, url)
                    result = {
                        'product_url': url,
                        'specifications': specs,
                        'count': len(specs),
                        'success': len(specs) > 0
                    }
                    batch_results.append(result)
                    
                    if len(specs) > 0:
                        self.logger.info(f"✅ {url.split('/')[-1][:30]}... -> {len(specs)} 规格")
                        
                except Exception as e:
                    self.logger.error(f"❌ 提取失败 {url}: {e}")
                    batch_results.append({
                        'product_url': url,
                        'specifications': [],
                        'count': 0,
                        'success': False,
                        'error': str(e)
                    })
            
            # 清理线程的driver
            try:
                driver.quit()
            except:
                pass
                
            return batch_results
        
        # 将URL列表分配给各个线程
        batch_size = max(1, len(product_urls) // max_workers)
        url_batches = []
        
        for i in range(0, len(product_urls), batch_size):
            batch = product_urls[i:i + batch_size]
            if batch:
                url_batches.append(batch)
        
        # 确保最后一批URL被合并到前一批（避免单个URL占用一个线程）
        if len(url_batches) > max_workers and len(url_batches[-1]) < batch_size // 2:
            url_batches[-2].extend(url_batches[-1])
            url_batches.pop()
        
        self.logger.info(f"   任务分配: {len(url_batches)} 个批次，每批约 {batch_size} 个URL")
        
        with ThreadPoolExecutor(max_workers=len(url_batches)) as executor:
            # 提交所有任务
            futures = [
                executor.submit(process_url_batch, batch) 
                for batch in url_batches
            ]
            
            # 收集结果
            completed = 0
            for future in futures:
                try:
                    batch_results = future.result(timeout=300)  # 5分钟超时
                    results.extend(batch_results)
                    completed += len(batch_results)
                    
                    if completed % 10 == 0:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed
                        eta = (len(product_urls) - completed) / rate if rate > 0 else 0
                        self.logger.info(
                            f"   进度: {completed}/{len(product_urls)} "
                            f"({completed/len(product_urls)*100:.1f}%) "
                            f"速度: {rate:.1f} 个/秒 "
                            f"预计剩余: {eta:.0f} 秒"
                        )
                        
                except Exception as e:
                    self.logger.error(f"❌ 任务执行失败: {e}")
        
        # 统计
        success_cnt = sum(1 for r in results if r['success'])
        total_specs = sum(r['count'] for r in results)
        self.logger.info(f"批量完成: 成功 {success_cnt}/{len(product_urls)}, 总规格 {total_specs}")
        return {'results': results, 'summary': {'success_cnt': success_cnt, 'total_specs': total_specs}}

    def extract_specifications(self, product_url: str) -> Dict[str, Any]:
        """向后兼容的单产品提取接口（供旧流水线调用）"""
        driver = self._create_optimized_driver()
        try:
            specs = self._extract_specifications_with_driver(driver, product_url)
            return {
                'product_url': product_url,
                'specifications': specs,
                'count': len(specs),
                'success': len(specs) > 0
            }
        except Exception as e:
            self.logger.error(f"extract_specifications 失败: {e}")
            return {
                'product_url': product_url,
                'specifications': [],
                'count': 0,
                'success': False,
                'error': str(e)
            }
        finally:
            driver.quit() 