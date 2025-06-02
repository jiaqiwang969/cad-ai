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
        self.logger = logging.getLogger("opt-specifications")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            self.logger.addHandler(handler)
        self.logger.setLevel(log_level)
        # 防止日志向上传播，避免重复输出
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
        options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(40)
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
        self.logger.debug("尝试设置每页显示项目数为全部...")
        
        # 首先检查是否存在分页控件
        try:
            pagination_indicators = [
                "//*[contains(text(), 'Items per page')]",
                "//*[contains(text(), 'items per page')]", 
                "//*[contains(text(), 'out of') and contains(text(), 'items')]",
                "//*[contains(text(), 'Show') and contains(text(), 'entries')]"
            ]
            
            has_pagination = False
            for selector in pagination_indicators:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements and any(elem.is_displayed() for elem in elements):
                        has_pagination = True
                        self.logger.debug(f"检测到分页控件: {elements[0].text.strip()[:50]}...")
                        break
                except:
                    continue
            
            if not has_pagination:
                self.logger.debug("未检测到分页控件，可能是单页面，直接提取数据")
                return False
                
        except Exception as e:
            self.logger.debug(f"检测分页控件时出错: {e}")
                return False
        
        # 策略1: 寻找分页区域中的数字和下拉控件
        try:
            self.logger.debug("策略1: 查找分页区域的控件...")
            
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
                        # 获取包含分页信息的最外层容器
                        for elem in elements:
                            # 查找父容器
                            for level in range(1, 4):  # 向上查找3层
                                try:
                                    container = elem.find_element(By.XPATH, f"./ancestor::*[{level}]")
                                    container_text = container.text.lower()
                                    if 'items per page' in container_text or 'out of' in container_text:
                                        pagination_container = container
                                        self.logger.debug(f"找到分页容器，文本: {container.text[:100]}...")
                                        break
                                except:
                                    continue
                            if pagination_container:
                                break
                    if pagination_container:
                        break
                except:
                    continue
            
            if pagination_container:
                # 在分页容器中查找所有可点击的数字
                self.logger.debug("在分页容器中查找可点击数字...")
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
                
                for selector in clickable_selectors:
                    try:
                        elements = pagination_container.find_elements(By.XPATH, selector)
                        for elem in elements:
                            elem_text = elem.text.strip()
                            elem_tag = elem.tag_name
                            
                            self.logger.debug(f"找到可点击元素: {elem_tag} '{elem_text}'")
                            
                            # 如果是select，检查选项
                            if elem_tag == 'select':
                                options = elem.find_elements(By.TAG_NAME, 'option')
                                option_texts = [opt.text.strip() for opt in options]
                                self.logger.debug(f"选项: {option_texts}")
                                
                                # 查找All或大数字选项
                                for opt in options:
                                    text = opt.text.strip().lower()
                                    if text in ['all', '全部'] or (text.isdigit() and int(text) >= 50):
                                        self.logger.debug(f"选择: {opt.text}")
                                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", opt)
                                        time.sleep(1)
                                        opt.click()
                                        time.sleep(5)
                                        return True
                            
                            # 如果是数字文本且可点击，尝试点击
                            elif elem.is_displayed() and elem.is_enabled():
                                if elem_text.isdigit() or elem_text.lower() in ['all', '全部']:
                                    try:
                                        self.logger.debug(f"尝试点击: {elem_text}")
                                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                                        time.sleep(1)
                                        elem.click()
                                        time.sleep(3)
                                        
                                        # 查找弹出菜单中的All选项
                                        self.logger.debug("查找弹出菜单中的All选项...")
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
                                                for all_option in all_options:
                                                    if all_option.is_displayed() and all_option.is_enabled():
                                                        self.logger.debug(f"找到All选项: {all_option.text} ({all_option.tag_name})")
                                                        all_option.click()
                                                        self.logger.debug("成功选择All选项！")
                                                        time.sleep(5)
                                                        all_found = True
                                                        return True
                                            except Exception as e:
                                                continue
                                        
                                        if not all_found:
                                            # 如果没找到All，尝试找最大数字
                                            self.logger.debug("未找到All，查找最大数字选项...")
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
                                                            self.logger.debug(f"选择最大数字: {max_option.text}")
                                                            max_option.click()
                                                            time.sleep(5)
                                                            return True
                                                except:
                                                    continue
                                            
                                            self.logger.debug("点击后未找到合适的选项")
                                        
                                    except Exception as e:
                                        self.logger.debug(f"点击失败: {e}")
                                        
                    except Exception as e:
                        self.logger.debug(f"查找元素失败: {e}")
                        
        except Exception as e:
            self.logger.debug(f"策略1失败: {e}")
        
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
                break
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
        
        self.logger.debug("所有策略都未能找到可用的分页控件")
        return False
    
    def _is_valid_product_reference(self, text: str) -> bool:
        """判断文本是否是有效的产品编号（完全复制测试脚本）"""
        if not text or len(text) < 3:
            return False
        
        # 排除明显的产品描述
        if any(desc_word in text.lower() for desc_word in [
            'aluminum', 'extrusion', 'description', 'purchasing', 'links', 
            'manufacturer', 'jlcmc', 'product page', 'plastic', 'mounting',
            'angle', 'brackets', 'winco', 'type'
        ]):
            return False
        
        # 支持多种产品编号格式
        patterns = [
            r'^TXCE-[A-Z0-9]+-[0-9]+-[0-9]+-L[0-9]',  # TXCE系列
            r'^[A-Z]{2,4}-[0-9]',                      # 通用格式如 EN-561
            r'^[0-9]{3,}-[A-Z0-9]',                    # 数字开头格式
            r'^[A-Z][0-9]+[A-Z]*$',                    # 字母+数字格式
            r'^[A-Z]{2,}-[A-Z0-9]{2,}',               # 字母-字母数字格式
        ]
        
        # 检查是否匹配任何模式
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # 进一步验证：必须有字母和数字
                if (any(char.isalpha() for char in text) and 
                    any(char.isdigit() for char in text)):
                    # 排除过长的文本（可能是描述）
                    if len(text) <= 50:
                    return True
        
        return False
    
    def _extract_dimensions_from_cells(self, cells: List[str]) -> str:
        """从单元格中提取尺寸信息（复制测试脚本）"""
        for cell_text in cells:
            dimension_match = re.search(r'\d+x\d+x?\d*', cell_text)
            if dimension_match:
                return dimension_match.group()
        return ''
    
    def _extract_weight_from_cells(self, cells: List[str]) -> str:
        """从单元格中提取重量或长度信息（复制测试脚本）"""
        for cell_text in cells:
            measure_match = re.search(r'(\d+[,\.]\d+|\d+)\s*(mm|kg|m|cm)', cell_text.lower())
            if measure_match:
                return measure_match.group()
        return ''
    
    def _extract_all_specifications(self, driver) -> List[Dict[str, Any]]:
        """提取所有产品规格（完全复制测试脚本）"""
        self.logger.debug("开始提取所有产品规格...")
        
        specifications = []
        seen_references = set()
        
        try:
            # 等待页面稳定
            time.sleep(3)
            
            # 完整滚动页面
            self._scroll_page_fully(driver)
            
            # 查找表格
            self.logger.debug("查找产品规格表格...")
            tables = driver.find_elements(By.TAG_NAME, 'table')
            
            if not tables:
                self.logger.warning("未找到任何表格")
                return specifications
            
            # 选择最大的表格
            best_table = max(tables, key=lambda t: len(t.find_elements(By.TAG_NAME, 'tr')))
            rows = best_table.find_elements(By.TAG_NAME, 'tr')
            
            self.logger.debug(f"找到最佳表格，共 {len(rows)} 行")
            
            # 分析表格结构
            header_row = None
            data_rows = []
            
            for i, row in enumerate(rows):
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                if not cells:
                    continue
                    
                cell_texts = [cell.text.strip() for cell in cells]
                
                # 判断是否为表头行
                is_header = any(keyword in ' '.join(cell_texts).lower() for keyword in [
                    'part number', 'product', 'reference', 'model', 'specification'
                ])
                
                if is_header and header_row is None:
                    header_row = i
                    self.logger.debug(f"识别表头行 {i+1}: {cell_texts[:3]}...")
                elif not is_header and len(cell_texts) > 1:
                    data_rows.append({'index': i, 'cells': cell_texts})
            
            self.logger.debug(f"识别出 {len(data_rows)} 行数据")
            
            # 提取产品规格
            for row_info in data_rows:
                row_index = row_info['index']
                cells = row_info['cells']
                
                # 查找产品编号（注意：这里是遍历所有cells，不是只查找前几列）
                found_reference = None
                for cell_text in cells:
                    if self._is_valid_product_reference(cell_text) and cell_text not in seen_references:
                        found_reference = cell_text
                        break
                
                if found_reference:
                    spec_info = {
                        'product_reference': found_reference,
                        'row_index': row_index,
                        'dimensions': self._extract_dimensions_from_cells(cells),
                        'weight': self._extract_weight_from_cells(cells),
                        'all_cells': cells,
                        'description': '',  # 添加description字段以保持兼容
                        'all_values': ' '.join(cells)  # 添加all_values字段
                    }
                    
                    specifications.append(spec_info)
                    seen_references.add(found_reference)
                    
                    if len(specifications) <= 10:  # 只显示前10个
                        self.logger.debug(f"规格 {len(specifications)}: {found_reference} ({spec_info['dimensions']})")
            
            if len(specifications) > 10:
                self.logger.debug(f"... 还有 {len(specifications) - 10} 个规格")
                
        except Exception as e:
            self.logger.error(f"提取规格时出错: {e}")
        
        self.logger.info(f"总共提取到 {len(specifications)} 个产品规格")
        return specifications
    
    def _extract_specifications_once(self, product_url: str) -> List[Dict[str, Any]]:
        """单次尝试提取产品规格（严格按照测试脚本）"""
        driver = None
        
        try:
            driver = self._create_optimized_driver()
            self.logger.debug(f"访问产品页面: {product_url}")
            driver.get(product_url)
            time.sleep(3)
            
            # 尝试设置每页显示为全部
            items_per_page_success = self._set_items_per_page_to_all(driver)
            
            if items_per_page_success:
                self.logger.debug("成功设置显示全部项目")
            else:
                self.logger.debug("单页面模式：直接提取当前页面数据")
            
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