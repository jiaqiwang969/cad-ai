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
from typing import List, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class OptimizedSpecificationsCrawler:
    """优化版产品规格爬取器"""
    
    def __init__(self, log_level: int = logging.INFO):
        """初始化优化版规格爬取器"""
        # 简单日志设置 (一次性)
        self.logger = logging.getLogger(__name__) # 使用 __name__ 获取当前模块的logger
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            # 更详细的日志格式
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(log_level)
        self.logger.propagate = False
        
        # 常量配置
        self.TIMEOUT = 60
        self.MAX_RETRY = 3
    
    def _create_optimized_driver(self):
        """创建优化的驱动（与测试脚本一致）"""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        # 更新User-Agent使其与修复脚本一致
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=options)
        # 增加隐式等待
        driver.implicitly_wait(10) 
        driver.set_page_load_timeout(self.TIMEOUT) # 使用类属性
        return driver
    
    def _scroll_page_fully(self, driver):
        """完整滚动页面确保所有内容加载（与测试脚本一致）"""
        self.logger.debug("滚动页面确保内容完全加载...")
        
        # 先滚动到底部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # 再滚动到顶部
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # 最后滚动到页面中部
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)
    
    def _set_items_per_page_to_all(self, driver) -> bool:
        """设置每页显示项目数为全部（完全复制测试脚本）"""
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
                                            time.sleep(5)
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
                                                        all_option.click()
                                                        self.logger.debug("✅ 成功选择All选项！")
                                                        time.sleep(5)
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
                                                            max_option.click()
                                                            time.sleep(5)
                                                            return True
                                                except:
                                                    continue
                                            
                                            self.logger.debug("⚠️ 点击后未找到合适的选项")
                                        
                                    except Exception as e:
                                        self.logger.warning(f"❌ 点击失败: {e}")
                                        
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
                                        opt.click()
                                        time.sleep(5)
                                        return True
                            else:
                                # 如果是可点击元素，尝试点击
                                try:
                                    self.logger.debug(f"点击数字控件: {elem_text}")
                                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                                    time.sleep(1)
                                    elem.click()
                                    time.sleep(3)
                                    
                                    # 查找弹出菜单中的All选项
                                    all_options = driver.find_elements(By.XPATH, "//li[normalize-space(.)='All'] | //option[normalize-space(.)='All'] | //*[@role='option'][normalize-space(.)='All']")
                                    for opt in all_options:
                                        if opt.is_displayed():
                                            opt.click()
                                            self.logger.debug("选择了All选项")
                                            time.sleep(5)
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
                            elif text.isdigit() and int(text) >= 50:
                                best_option = opt
                        
                        if best_option:
                            self.logger.debug(f"选择: {best_option.text}")
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", best_option)
                            time.sleep(1)
                            best_option.click()
                            time.sleep(5)
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
        """增强版产品编号判断 (来自修复脚本)"""
        if not text or len(text) < 3: # 太短的文本不太可能是编号
            return False
        
        text = str(text) # 确保是字符串

        # 排除明显的非产品编号
        exclude_patterns = [
            r'^https?://',  # URL
            r'^www\\.',      # 网址
            r'@',           # 邮箱
            r'^\d{4}-\d{2}-\d{2}',  # 日期 YYYY-MM-DD
            r'^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}', # 其他日期格式 DD/MM/YYYY etc.
            r'^\+?\d[\d\s-]{7,}$',  # 电话号码 (更通用)
            r'^[\s\-_.,;:!?]*$',  # 只有空格和标点
            r'^(select|choose|option|view|details|more|info|click|here|page|item|price|currency|total|sum|average)$', # 常见按钮/指令词
            r'^(january|february|march|april|may|june|july|august|september|october|november|december)$', # 月份全称
            r'^(mon|tue|wed|thu|fri|sat|sun)$' # 星期缩写
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.debug(f"'{text}' 被排除 (规则: {pattern})")
                return False
        
        # 排除常见描述词 (更广泛)
        common_words = [
            'description', 'manufacturer', 'material', 'color', 'size', 'type', 'style', 'model',
            'weight', 'length', 'width', 'height', 'depth', 'diameter', 'thickness', 'volume',
            'please', 'select', 'bearing', 'unit', 'assembly', 'component', 'part', 'parts',
            'mounted', 'not', 'items', 'per', 'page', 'documentation', 'document', 'pdf', 'cad',
            'contact', 'supplier', 'provider', 'seller', 'data', 'sheet', 'specification', 'specs',
            'disclaimer', 'liability', 'information', 'details', 'overview', 'summary', 'notes',
            'available', 'unavailable', 'status', 'stock', 'inventory', 'quantity', 'amount',
            'accessory', 'accessories', 'optional', 'standard', 'feature', 'features', 'benefit',
            'application', 'usage', 'instruction', 'manual', 'guide', 'help', 'support', 'faq',
            'series', 'version', 'revision', 'edition', 'release', 'date', 'time', 'update',
            # 多语言常见词 (示例)
            'descripción', 'fabricante', 'tamaño', 'peso', 'longitud', # 西班牙语
            'beschreibung', 'hersteller', 'farbe', 'größe', 'gewicht', # 德语
            'taille', 'poids', 'longueur', 'largeur', 'hauteur', # 法语
            '说明', '描述', '制造商', '颜色', '尺寸', '重量', '长度', '型号', '系列' # 中文
        ]
        
        text_lower_words = re.findall(r'\b\w+\b', text.lower())
        # 如果文本由多个常见词组成，则排除
        if len(text_lower_words) > 1 and all(word in common_words for word in text_lower_words):
            self.logger.debug(f"'{text}' 被排除 (常见描述词组合)")
            return False
        # 如果单个词是常见词也排除 (除非它也符合强积极指标)
        if len(text_lower_words) == 1 and text_lower_words[0] in common_words:
             # 允许像 'CAD' 或 'PDF' 这样的单个常见词，如果它们也像编号
            if not (any(c.isupper() for c in text) and any(c.isdigit() for c in text)):
                self.logger.debug(f"'{text}' 被排除 (单个常见描述词)")
                return False

        # 积极指标
        positive_score = 0
        
        # 1. 包含数字
        if any(c.isdigit() for c in text):
            positive_score += 2
        
        # 2. 包含连字符、下划线、点（非句末）或斜杠
        if re.search(r'[-_./]', text.strip('.')): # strip('.') 避免句末的点影响判断
            positive_score += 1
        
        # 3. 包含大写字母（混合大小写或全大写）
        if any(c.isupper() for c in text) and not text.islower():
            positive_score += 1
            if text.isupper() and len(text) > 1: # 全大写且不止一个字符
                 positive_score +=1
        
        # 4. 长度适中
        if 3 <= len(text) <= 60: # 放宽最大长度
            positive_score += 1
        else:
            positive_score -=1 # 过长或过短扣分

        # 5. 数字和字母混合
        if any(c.isdigit() for c in text) and any(c.isalpha() for c in text):
            positive_score += 2

        # 6. 特殊格式模式 (更通用和全面)
        special_patterns = [
            r'^[A-Z0-9]+([-/_.][A-Z0-9]+)+$',  # ABC-123-DEF, 123.456.XYZ, a/b-1
            r'^[A-Z]{1,5}\d{2,}(\s?[-/_.]?[A-Z0-9]+)*$',     # USC201T20, DIN933, MS24693-C2
            r'^\d+[A-Z]{1,5}(\s?[-/_.]?[A-Z0-9]+)*$',     # 200T20ABC
            r'^[A-Z0-9]+[-_./][A-Z0-9]+[-_./]?[A-Z0-9]*$',  # QAAMC10A050S, complex codes
            r'^(P/N|PN|SKU|REF|ITEM|MODEL|NO|ART)\s*[:.#-]?\s*\S+', # 以常见前缀开头
            r'^\S*-\d+/\d+$' # e.g. ABC-12/34
        ]
        
        for pattern in special_patterns:
            if re.match(pattern, text, re.IGNORECASE): # 忽略大小写匹配模式
                self.logger.debug(f"'{text}' 匹配特殊模式: {pattern}")
                positive_score += 3
                break 
        
        # 7. 包含多个大写字母或数字组合 (非纯文本)
        if len(re.findall(r'[A-Z0-9]{2,}', text)) > 1 :
            positive_score +=1

        self.logger.debug(f"'{text}' 的最终产品编号评分为: {positive_score}")
        return positive_score >= 4 # 提高阈值，要求更强的信号

    def _extract_all_specifications(self, driver) -> List[Dict[str, Any]]:
        """提取所有产品规格——复刻 test/09-1 的完整逻辑"""
        specs: List[Dict[str, Any]] = []
        seen_refs = set()
        
        try:
            # 确保页面稳定并滚动一次
            time.sleep(2)
            self._scroll_page_fully(driver)

            # 1️⃣ 通过标题定位"产品选择"表格
            section_keywords = [
                'product selection', 'product list', 'product specifications',
                'available products', 'product variants', 'models available',
                'produktauswahl', 'produktliste', 'produktspezifikationen',  # 德语
                'sélection de produits', 'liste des produits',              # 法语
                '产品选择', '产品列表', '产品规格',                            # 中文
                'specification', 'specifications', 'technical data'
            ]
            table_elem = None
            header_elem = None

            for kw in section_keywords:
                xpath_list = [
                    f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}')]",
                    f"//h1[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}')]",
                    f"//h2[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}')]",
                    f"//h3[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}')]",
                    f"//h4[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{kw.lower()}')]",
                ]
                found = False
                for xp in xpath_list:
                    try:
                        elems = driver.find_elements(By.XPATH, xp)
                        for elem in elems:
                            if elem.is_displayed() and elem.text.strip():
                                # 寻找该元素附近的表格
                                parent = elem
                                candidate_tables = []
                                # ① 同一父容器
                                try:
                                    container = elem.find_element(By.XPATH, './..')
                                    candidate_tables.extend(container.find_elements(By.TAG_NAME, 'table'))
                                except:  # noqa: E722
                                    pass
                                # ② 后续兄弟
                                candidate_tables.extend(elem.find_elements(By.XPATH, './following-sibling::*//table'))
                                # ③ 整个文档后续
                                candidate_tables.extend(elem.find_elements(By.XPATH, './following::table'))
                                candidate_tables = [t for t in candidate_tables if t.is_displayed()]
                                if candidate_tables:
                                    table_elem = candidate_tables[0]
                                    header_elem = elem
                                    found = True
                                    break
                        if found:
                            break
                    except Exception:
                        continue
                if found:
                    break

            # 2️⃣ 如果标题法没找到，就在全部可见表格里打分挑选
            if not table_elem:
                tables = [t for t in driver.find_elements(By.TAG_NAME, 'table') if t.is_displayed()]
                best_score = -1
                for t in tables:
                    rows = t.find_elements(By.TAG_NAME, 'tr')
                    score = 0
                    for r in rows[:10]:  # 前10行
                        cells = r.find_elements(By.CSS_SELECTOR, 'td, th')
                        cell_texts = [self._get_cell_text_enhanced(c) for c in cells]
                        non_empty = [c for c in cell_texts if c]
                        if len(non_empty) >= 2:
                            score += len(non_empty)
                            # 加分：出现编号关键词或可能编号
                            for txt in non_empty:
                                tl = txt.lower()
                                if any(k in tl for k in ['part', 'number', 'model', 'reference', 'item']):
                                    score += 5
                                if self._is_likely_product_reference_enhanced(txt):
                                    score += 3
                    if score > best_score:
                        best_score = score
                        table_elem = t

            if not table_elem:
                self.logger.warning("❌ 未找到任何合适的规格表格")
                return specs

            rows = table_elem.find_elements(By.TAG_NAME, 'tr')
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
                    if prop_val and prop_val not in seen_refs and self._is_likely_product_reference_enhanced(prop_val):
                        spec = {
                            'reference': prop_val,
                            'row_index': idx,
                            'property_name': prop_name,
                            'dimensions': self._extract_dimensions_from_cells([prop_val]),
                            'weight': self._extract_weight_from_cells([prop_val]),
                            'table_type': 'vertical'
                        }
                        specs.append(spec)
                        seen_refs.add(prop_val)
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
                        for kw in [
                            'part number','part no','part#','p/n','product number','product code','model','reference',
                            'item number','catalog number','sku','description','bestellnummer','artikelnummer','teilenummer',
                            '型号','编号','料号'
                        ]:
                            if kw in h_l:
                                product_cols.append(j)
                                break
                    if len(product_cols) > 1:
                        product_cols = product_cols[:1]
                use_smart = not product_cols

                for i, r in enumerate(rows):
                    if i <= header_idx:
                        continue
                    cells = r.find_elements(By.CSS_SELECTOR, 'td, th')
                    cell_texts = [self._get_cell_text_enhanced(c) for c in cells]
                    if not cell_texts:
                        continue
                    found_in_row = False
                    if use_smart:
                        for j, txt in enumerate(cell_texts):
                            if txt and txt not in seen_refs and self._is_likely_product_reference_enhanced(txt):
                                spec = {
                                    'reference': txt,
                                    'row_index': i,
                                    'column_index': j,
                                    'column_name': header_cells_text[j] if header_cells_text and j < len(header_cells_text) else '',
                                    'dimensions': self._extract_dimensions_from_cells(cell_texts),
                                    'weight': self._extract_weight_from_cells(cell_texts),
                                    'table_type': 'horizontal'
                                }
                                specs.append(spec)
                                seen_refs.add(txt)
                                found_in_row = True
                                break
                    else:
                        for col in product_cols:
                            if col < len(cell_texts):
                                txt = cell_texts[col]
                                if txt and txt not in seen_refs and self._is_likely_product_reference_enhanced(txt):
                                    spec = {
                                        'reference': txt,
                                        'row_index': i,
                                        'column_index': col,
                                        'column_name': header_cells_text[col] if col < len(header_cells_text) else '',
                                        'dimensions': self._extract_dimensions_from_cells(cell_texts),
                                        'weight': self._extract_weight_from_cells(cell_texts),
                                        'table_type': 'horizontal'
                                    }
                                    specs.append(spec)
                                    seen_refs.add(txt)
                                    found_in_row = True
                                    break
            return specs
        except Exception as e:
            self.logger.error(f"提取规格时发生异常: {e}")
            return specs

    def _close_disclaimer_popup(self, driver, timeout: int = 10) -> bool:
        """检测并关闭免责声明/许可协议弹窗（支持 iframe 内按钮）"""
        self.logger.debug("[POPUP] 检测免责声明弹窗…")
        accept_keywords = [
            'i understand and accept', 'i understand', 'accept', 'agree',
            'continue', 'ok', 'yes', 'proceed',
            '我理解并接受', '我理解', '接受', '同意', '确认', '继续'
        ]

        # 尝试等待弹窗出现（通过iframe或modal类）
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: any(
                    elem.is_displayed() and elem.size['width'] > 200 and elem.size['height'] > 100
                    for elem in d.find_elements(By.XPATH,
                        "//iframe | //div[contains(@class,'modal') or contains(@class,'popup') or contains(@class,'dialog') or contains(@class,'overlay')]")
                )
            )
        except TimeoutException:
            self.logger.debug("[POPUP] 未检测到弹窗")
            return False

        # 在主文档中查找按钮
        for kw in accept_keywords:
            try:
                btn = driver.find_element(By.XPATH,
                    f"//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')]" )
                if btn.is_displayed() and btn.is_enabled():
                    self.logger.debug(f"[POPUP] 点击按钮: {btn.text.strip()}")
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    btn.click()
                    time.sleep(2)
                    return True
            except Exception:
                continue

        # 检查所有 iframe
        for iframe in driver.find_elements(By.TAG_NAME, 'iframe'):
            if not iframe.is_displayed():
                continue
            try:
                driver.switch_to.frame(iframe)
                for kw in accept_keywords:
                    try:
                        btn = driver.find_element(By.XPATH,
                            f"//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')] | //a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')]")
                        if btn.is_displayed() and btn.is_enabled():
                            self.logger.debug(f"[POPUP] 在iframe点击按钮: {btn.text.strip()}")
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                            btn.click()
                            driver.switch_to.default_content()
                            time.sleep(2)
                            return True
                    except Exception:
                        continue
                driver.switch_to.default_content()
            except Exception:
                driver.switch_to.default_content()
                continue
        self.logger.warning("[POPUP] 无法关闭免责声明弹窗")
        return False

    def _extract_specifications_once(self, product_url: str) -> List[Dict[str, Any]]:
        """单次尝试提取产品规格（严格按照测试脚本）"""
        driver = None
        
        try:
            driver = self._create_optimized_driver()
            self.logger.debug(f"访问产品页面: {product_url}")
            driver.get(product_url)
            time.sleep(3)
            
            # NEW: 先关闭免责声明弹窗
            self._close_disclaimer_popup(driver)
            
            # 尝试设置每页显示为全部
            self.logger.info("🔧 开始处理分页设置...")
            items_per_page_success = self._set_items_per_page_to_all(driver)
            
            if items_per_page_success:
                self.logger.info("✅ 成功设置显示全部项目 - 应该能看到所有规格")
            else:
                self.logger.warning("⚠️ 分页设置失败 - 可能只能看到当前页面的规格")
            
            # 确保页面完全加载
            self._scroll_page_fully(driver)
            
            # 提取所有规格信息
            specifications = self._extract_all_specifications(driver)
            
            self.logger.info(f"从 {product_url} 提取到 {len(specifications)} 个规格")
            
            return specifications
            
        except TimeoutException:
            self.logger.warning(f"页面加载超时: {product_url}")
            raise
        except Exception as e:
            self.logger.error(f"提取规格失败: {e}")
            raise
        finally:
            if driver:
                driver.quit()
    
    def extract_specifications(self, product_url: str) -> Dict[str, Any]:
        """提取产品规格（带重试）"""
        for attempt in range(1, self.MAX_RETRY + 1):
            try:
                specifications = self._extract_specifications_once(product_url)
                return {
                    'product_url': product_url,
                    'specifications': specifications,
                    'count': len(specifications),
                    'success': True
                }
                
            except (TimeoutException, Exception) as e:
                if attempt < self.MAX_RETRY:
                    self.logger.warning(f"尝试 {attempt}/{self.MAX_RETRY} 失败，重试: {product_url}")
                    time.sleep(2)
                else:
                    self.logger.error(f"达到最大重试次数，放弃: {product_url}")
                    
        # 返回失败结果
        return {
            'product_url': product_url,
            'specifications': [],
            'count': 0,
            'success': False,
            'error': 'retry_failed'
        }
    
    def extract_batch_specifications(self,
                                   product_urls: List[str],
                                   max_workers: int = 16) -> List[Dict[str, Any]]:
        """批量提取产品规格 (简化版，串行处理)"""
        results = []
        total = len(product_urls)
        
        self.logger.info(f"开始批量提取 {total} 个产品的规格信息")
        
        for i, url in enumerate(product_urls):
            if i % 10 == 0:  # 每10个产品记录一次进度
                self.logger.info(f"进度: {i}/{total} ({i/total*100:.1f}%)")
            
            result = self.extract_specifications(url)
            results.append(result)
        
        # 统计
        success_count = sum(1 for r in results if r['success'])
        total_specs = sum(r['count'] for r in results)
        
        self.logger.info(
            f"批量提取完成: {success_count}/{total} 个产品成功, "
            f"共 {total_specs} 个规格"
        )
        
        return results 