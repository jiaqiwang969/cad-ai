#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Winco 产品分页规格提取
测试通用逻辑是否能处理需要翻页的产品页面
运行: python3 scripts/test_winco_pagination.py
"""
import os, sys, time, re, json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("❌ Selenium 未安装，无法运行测试！")
    sys.exit(1)

RESULTS_DIR = Path("results/winco_pagination_test")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 测试产品URL
TEST_URL = "https://www.traceparts.cn/en/product/jw-winco-din-787-metric-size-steel-tslot-bolts?CatalogPath=TRACEPARTS%3ATP01001013006&Product=90-04092020-049501"

# 通用料号识别正则（放宽限制）
REFERENCE_PATTERN = re.compile(r'^[A-Z0-9\-_/\s]{4,50}$', re.IGNORECASE)

# 需要排除的词汇（通常不是料号）
EXCLUDE_WORDS = [
    'tools', 'engineering', 'company', 'corporation', 'website',
    'http', 'https', 'www', '.com', '.cn', '.org', '.net',
    'download', 'catalog', 'datasheet', 'manual', 'guide',
    'home', 'about', 'contact', 'support', 'service'
]

# 尺寸和重量提取正则
DIMENSION_PATTERN = re.compile(r'\b\d+(?:\.\d+)?[x×]\d+(?:\.\d+)?(?:[x×]\d+(?:\.\d+)?)?\b', re.IGNORECASE)
WEIGHT_PATTERN = re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(kg|g|lb|lbs|oz)\b', re.IGNORECASE)
LENGTH_PATTERN = re.compile(r'\b(\d+(?:[.,]\d+)?)\s*(mm|cm|m|in|ft)\b', re.IGNORECASE)

# 属性名关键词（用于识别纵向表）
PROPERTY_KEYWORDS = [
    'manufacturer', 'part number', 'weight', 'dimension', 'size', 
    'material', 'color', 'length', 'width', 'height', 'diameter',
    'thickness', 'bore', 'model', 'series', 'type'
]

# 表头关键词
HEADER_KEYWORDS = [
    'part number', 'reference', 'model', 'specification', 'description',
    'part no', 'item no', 'catalog', '型号', '编号'
]

def prepare_driver():
    """准备Chrome驱动器"""
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

def scroll_page_fully(driver):
    """完整滚动页面确保所有内容加载"""
    print("🔄 滚动页面确保内容完全加载...")
    
    # 先滚动到底部
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # 再滚动到顶部
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 最后滚动到页面中部
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(1)

def is_valid_reference(text: str) -> bool:
    """判断是否为有效的产品料号（通用版）"""
    if not text or len(text) < 4:
        return False
    
    # 去除前后空格
    text = text.strip()
    
    # 排除包含 " - " 后跟描述的格式（如 "1 - Without cover cap"）
    if ' - ' in text:
        parts = text.split(' - ')
        if len(parts) == 2:
            # 第一部分是数字，第二部分包含字母，通常是描述
            if parts[0].strip().isdigit() and any(c.isalpha() for c in parts[1]):
                return False
    
    # 排除纯数字且长度为8的（可能是分类码如 ECLASS）
    if text.isdigit() and len(text) == 8:
        return False
    
    # 排除纯数字且长度超过10的（太长的数字通常不是料号）
    if text.isdigit() and len(text) > 10:
        return False
    
    # 排除 URL
    if text.startswith(('http://', 'https://', 'www.')):
        return False
    
    # 排除包含域名后缀的文本
    if any(domain in text.lower() for domain in ['.com', '.cn', '.org', '.net', '.edu']):
        return False
    
    # 排除包含特定词汇的文本
    text_lower = text.lower()
    if any(word in text_lower for word in EXCLUDE_WORDS):
        return False
    
    # 排除过长的文本（料号通常不会很长）
    if len(text) > 30:
        return False
    
    # Winco 特殊料号格式（如 DIN787-M10-20-ST）
    if text.startswith('DIN') and '-' in text:
        return True
    
    # 特殊情况：可能只有数字（如轴承型号）
    if text.isdigit() and len(text) >= 4:
        return True
    
    # 包含斜杠的型号（如 25580/25520）
    if '/' in text and len(text) >= 5:
        parts = text.split('/')
        if all(part.strip() and not part.strip().isalpha() for part in parts):
            return True
    
    # 包含空格的型号（如 FSAF 22528 x 5）- 但要确保不是普通英文
    if ' ' in text:
        # 检查是否为型号格式（字母+数字组合）
        parts = text.split()
        if len(parts) <= 5:  # 型号通常不会有太多部分
            has_model_pattern = any(
                (any(c.isalpha() for c in part) and any(c.isdigit() for c in part)) or
                part.isdigit() or
                part in ['x', 'X', '-', '/']
                for part in parts
            )
            if has_model_pattern:
                return True
    
    # 通用规则：包含字母和数字，但排除句子
    has_letter = any(c.isalpha() for c in text)
    has_number = any(c.isdigit() for c in text)
    
    # 排除纯英文句子（连续的字母太多）
    if has_letter and not has_number:
        # 统计连续字母的最大长度
        max_letter_seq = 0
        current_seq = 0
        for c in text:
            if c.isalpha():
                current_seq += 1
                max_letter_seq = max(max_letter_seq, current_seq)
            else:
                current_seq = 0
        # 如果连续字母超过10个，可能是单词而不是型号
        if max_letter_seq > 10:
            return False
    
    if has_letter and has_number:
        # 匹配通用料号模式
        return bool(REFERENCE_PATTERN.match(text))
    
    return False

def classify_row(cells: List[str]) -> str:
    """判断行的类型：header/property/data"""
    if not cells:
        return 'empty'
    
    # 合并所有单元格文本（小写）
    row_text = ' '.join(cells).lower()
    
    # 检查是否为表头行
    if any(keyword in row_text for keyword in HEADER_KEYWORDS):
        return 'header'
    
    # 检查是否为属性-值行（2列）
    if len(cells) == 2:
        first_cell = cells[0].lower()
        if any(keyword in first_cell for keyword in PROPERTY_KEYWORDS):
            return 'property'
    
    # 默认为数据行
    return 'data'

def extract_dimensions_weight(cells: List[str]) -> Dict[str, str]:
    """从单元格列表中提取尺寸和重量信息"""
    result = {'dimensions': '', 'weight': '', 'length': ''}
    
    for cell in cells:
        if not result['dimensions']:
            dim_match = DIMENSION_PATTERN.search(cell)
            if dim_match:
                result['dimensions'] = dim_match.group()
        
        if not result['weight']:
            weight_match = WEIGHT_PATTERN.search(cell)
            if weight_match:
                result['weight'] = weight_match.group()
        
        if not result['length']:
            length_match = LENGTH_PATTERN.search(cell)
            if length_match:
                result['length'] = length_match.group()
    
    return result

def parse_table_universal(table_element) -> List[Dict[str, Any]]:
    """通用表格解析器"""
    print("📊 开始解析表格...")
    
    specifications = []
    current_spec = None
    seen_references = set()
    
    # 获取所有行
    rows = table_element.find_elements(By.TAG_NAME, 'tr')
    print(f"  找到 {len(rows)} 行")
    
    for i, row in enumerate(rows):
        # 获取所有单元格（td 和 th）
        cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
        if not cells:
            continue
        
        # 提取单元格文本
        cell_texts = [cell.text.strip() for cell in cells]
        if not any(cell_texts):  # 空行
            continue
        
        # 判断行类型
        row_type = classify_row(cell_texts)
        
        if row_type == 'header':
            print(f"  行 {i+1}: 表头行 - {cell_texts[:3]}...")
            continue
        
        elif row_type == 'property':
            # 纵向属性-值对
            prop_name = cell_texts[0].lower()
            prop_value = cell_texts[1] if len(cell_texts) > 1 else ''
            
            # 检查是否为料号属性
            if any(keyword in prop_name for keyword in ['part number', 'manufacturer part', 'model']):
                if is_valid_reference(prop_value) and prop_value not in seen_references:
                    # 创建新规格
                    if current_spec:
                        specifications.append(current_spec)
                    
                    current_spec = {
                        'product_reference': prop_value,
                        'dimensions': '',
                        'weight': '',
                        'description': '',
                        'properties': {}
                    }
                    seen_references.add(prop_value)
                    print(f"  行 {i+1}: 发现料号 - {prop_value}")
            
            # 添加属性到当前规格
            elif current_spec:
                current_spec['properties'][prop_name] = prop_value
                # 尝试提取尺寸和重量
                extra_info = extract_dimensions_weight([prop_value])
                for key, value in extra_info.items():
                    if value and not current_spec.get(key):
                        current_spec[key] = value
        
        elif row_type == 'data':
            # 横向数据行 - 查找料号
            found_reference = None
            ref_index = -1
            
            for j, cell_text in enumerate(cell_texts):
                if is_valid_reference(cell_text) and cell_text not in seen_references:
                    found_reference = cell_text
                    ref_index = j
                    break
            
            if found_reference:
                # 保存之前的规格
                if current_spec:
                    specifications.append(current_spec)
                
                # 创建新规格
                current_spec = {
                    'product_reference': found_reference,
                    'dimensions': '',
                    'weight': '',
                    'description': '',
                    'all_cells': cell_texts
                }
                
                # 提取尺寸和重量
                extra_info = extract_dimensions_weight(cell_texts)
                current_spec.update(extra_info)
                
                # 描述字段（排除料号本身）
                desc_cells = [cell_texts[j] for j in range(len(cell_texts)) if j != ref_index and cell_texts[j]]
                current_spec['description'] = ' | '.join(desc_cells[:3])  # 最多3个字段
                
                seen_references.add(found_reference)
                print(f"  行 {i+1}: 数据行 - 料号 {found_reference}")
    
    # 保存最后一个规格
    if current_spec:
        specifications.append(current_spec)
    
    print(f"✅ 从表格提取到 {len(specifications)} 个规格")
    return specifications

def handle_pagination(driver) -> int:
    """处理分页，返回找到的页数"""
    page_count = 1
    
    try:
        # 查找分页控件
        pagination = driver.find_element(By.CSS_SELECTOR, '.pagination, nav[aria-label="pagination"], .page-numbers')
        print("🔍 发现分页控件")
        
        # 查找所有页码链接
        page_links = pagination.find_elements(By.CSS_SELECTOR, 'a, button')
        page_numbers = []
        
        for link in page_links:
            text = link.text.strip()
            if text.isdigit():
                page_numbers.append(int(text))
        
        if page_numbers:
            page_count = max(page_numbers)
            print(f"📄 发现 {page_count} 页")
        
    except NoSuchElementException:
        print("📄 未发现分页（单页产品）")
    
    return page_count

def navigate_to_page(driver, page_num: int) -> bool:
    """导航到指定页码"""
    try:
        # 先滚动到页面底部，确保分页控件可见
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        
        # 查找页码链接
        page_link = driver.find_element(By.XPATH, f"//a[text()='{page_num}'] | //button[text()='{page_num}']")
        
        # 滚动到元素可见
        driver.execute_script("arguments[0].scrollIntoView(true);", page_link)
        time.sleep(1)
        
        # 使用JavaScript点击，避免被其他元素遮挡
        driver.execute_script("arguments[0].click();", page_link)
        time.sleep(3)  # 等待页面加载
        
        print(f"✅ 成功导航到第 {page_num} 页")
        return True
    except Exception as e:
        print(f"❌ 无法导航到第 {page_num} 页: {e}")
        
        # 尝试备选方案：查找其他可能的分页元素
        try:
            # 尝试查找data-page属性的元素
            page_link = driver.find_element(By.CSS_SELECTOR, f'[data-page="{page_num}"]')
            driver.execute_script("arguments[0].scrollIntoView(true);", page_link)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", page_link)
            time.sleep(3)
            print(f"✅ 使用备选方案成功导航到第 {page_num} 页")
            return True
        except:
            pass
        
        return False

def set_items_per_page_to_all(driver):
    """设置每页显示项目数为全部（借鉴 test-09-1 的方法）"""
    print("🎯 尝试设置每页显示项目数为全部...")
    
    # 首先检查是否存在分页控件
    try:
        # 查找是否有"Items per page"相关文本
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
                    print(f"  ✅ 检测到分页控件: {elements[0].text.strip()[:50]}...")
                    break
            except:
                continue
        
        if not has_pagination:
            print("  ℹ️ 未检测到分页控件，可能是单页面")
            return False
            
    except Exception as e:
        print(f"  ⚠️ 检测分页控件时出错: {e}")
        return False
    
    # 策略1: 寻找分页区域中的数字和下拉控件
    try:
        print("  🔍 策略1: 查找分页区域的控件...")
        
        # 查找当前显示数字的可点击元素（通常显示10）
        number_selectors = [
            "//select[option[text()='10']]",
            "//*[text()='10' and (@onclick or @role='button' or contains(@class,'select'))]",
            "//button[text()='10']",
            "//a[text()='10']",
            "//*[@data-value='10']"
        ]
        
        for selector in number_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        elem_tag = elem.tag_name
                        
                        if elem_tag == 'select':
                            # 如果是select，直接查找All选项
                            options = elem.find_elements(By.TAG_NAME, 'option')
                            for opt in options:
                                if opt.text.strip().lower() in ['all', '全部']:
                                    print(f"    ✅ 在select中选择: {opt.text}")
                                    opt.click()
                                    time.sleep(5)
                                    return True
                        else:
                            # 如果是可点击元素，先点击它
                            print(f"    🖱️ 点击数字控件: {elem.text}")
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                            time.sleep(1)
                            elem.click()
                            time.sleep(2)
                            
                            # 查找弹出菜单中的All选项
                            all_selectors = [
                                "//li[normalize-space(.)='All']",
                                "//div[normalize-space(.)='All']",
                                "//option[normalize-space(.)='All']",
                                "//*[@role='option'][normalize-space(.)='All']",
                                "//*[contains(@class,'option')][normalize-space(.)='All']"
                            ]
                            
                            for all_sel in all_selectors:
                                try:
                                    all_options = driver.find_elements(By.XPATH, all_sel)
                                    for all_option in all_options:
                                        if all_option.is_displayed():
                                            print(f"    ✅ 找到并点击All选项")
                                            all_option.click()
                                            time.sleep(5)
                                            return True
                                except:
                                    continue
                                    
            except Exception as e:
                print(f"    策略1遇到错误: {e}")
                
    except Exception as e:
        print(f"  ❌ 策略1失败: {e}")
    
    print("  ℹ️ 未能设置显示全部，将使用当前页面数据")
    return False

def extract_all_specifications_smart(driver) -> List[Dict[str, Any]]:
    """智能产品规格提取器（优先尝试全页加载）"""
    print("\n📋 使用智能提取器提取产品规格...")
    
    all_specifications = []
    
    try:
        # 等待页面稳定
        time.sleep(3)
        
        # 首先尝试设置显示全部项目
        show_all_success = set_items_per_page_to_all(driver)
        
        if show_all_success:
            print("✅ 成功设置显示全部项目，等待页面刷新...")
            time.sleep(3)
            
            # 再次截图确认
            timestamp = int(time.time())
            screenshot_path = RESULTS_DIR / f"after_show_all_{timestamp}.png"
            driver.save_screenshot(str(screenshot_path))
            print(f"📸 全页加载后截图: {screenshot_path}")
        
        # 完整滚动页面
        scroll_page_fully(driver)
        
        # 提取当前页面的所有数据
        tables = driver.find_elements(By.TAG_NAME, 'table')
        print(f"🔍 找到 {len(tables)} 个表格")
        
        # 解析每个表格
        for idx, table in enumerate(tables):
            print(f"\n处理表格 {idx + 1}/{len(tables)}:")
            
            # 获取表格行数预览
            rows = table.find_elements(By.TAG_NAME, 'tr')
            print(f"  表格规模: {len(rows)} 行")
            
            # 跳过太小的表格
            if len(rows) < 2:
                print("  跳过（行数太少）")
                continue
            
            # 解析表格
            specs = parse_table_universal(table)
            all_specifications.extend(specs)
        
        # 如果没有成功设置全页显示，且发现了分页，则使用分页逻辑
        if not show_all_success and len(all_specifications) < 50:
            print("\n⚠️ 检测到可能有更多数据，尝试分页处理...")
            
            # 检查是否有分页
            total_pages = handle_pagination(driver)
            
            if total_pages > 1:
                print(f"📄 发现 {total_pages} 页，开始逐页提取...")
                
                # 从第2页开始（第1页已处理）
                for page_num in range(2, total_pages + 1):
                    if navigate_to_page(driver, page_num):
                        time.sleep(2)
                        scroll_page_fully(driver)
                        
                        print(f"\n🔍 处理第 {page_num}/{total_pages} 页")
                        
                        # 重新查找表格（页面已刷新）
                        tables = driver.find_elements(By.TAG_NAME, 'table')
                        
                        for idx, table in enumerate(tables):
                            rows = table.find_elements(By.TAG_NAME, 'tr')
                            if len(rows) >= 2:
                                specs = parse_table_universal(table)
                                # 避免重复
                                for spec in specs:
                                    if not any(s['product_reference'] == spec['product_reference'] 
                                             for s in all_specifications):
                                        all_specifications.append(spec)
        
    except Exception as e:
        print(f"❌ 提取规格时出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 去重处理
    unique_specifications = []
    seen_references = set()
    for spec in all_specifications:
        ref = spec['product_reference']
        if ref not in seen_references:
            unique_specifications.append(spec)
            seen_references.add(ref)
    
    print(f"\n✅ 总共提取到 {len(unique_specifications)} 个唯一产品规格")
    return unique_specifications

def test_winco_pagination():
    """测试 Winco 分页产品"""
    print("🎯 Winco 分页产品规格提取测试")
    print(f"📌 测试URL: {TEST_URL}")
    
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium 未安装，无法运行！")
        return False
    
    driver = prepare_driver()
    
    try:
        # 访问产品页面
        print("\n🌐 访问产品页面...")
        driver.get(TEST_URL)
        time.sleep(3)
        
        # 截图
        timestamp = int(time.time())
        screenshot_path = RESULTS_DIR / f"winco_pagination_{timestamp}_page1.png"
        driver.save_screenshot(str(screenshot_path))
        print(f"📸 页面截图: {screenshot_path}")
        
        # 提取规格（智能提取）
        specifications = extract_all_specifications_smart(driver)
        
        # 构建结果
        result = {
            'product_name': 'JW Winco DIN 787 T-Slot Bolts',
            'product_url': TEST_URL,
            'timestamp': timestamp,
            'success': len(specifications) > 0,
            'specifications_count': len(specifications),
            'specifications': specifications,
            'screenshot': str(screenshot_path)
        }
        
        # 显示结果摘要
        print(f"\n📊 提取结果:")
        print(f"  成功: {result['success']}")
        print(f"  规格数量: {result['specifications_count']}")
        
        if specifications:
            print(f"\n  前10个规格:")
            for i, spec in enumerate(specifications[:10], 1):
                print(f"  {i}. {spec['product_reference']}")
                if spec.get('dimensions'):
                    print(f"     尺寸: {spec['dimensions']}")
                if spec.get('weight'):
                    print(f"     重量: {spec['weight']}")
                if spec.get('description'):
                    print(f"     描述: {spec['description'][:50]}...")
            
            if len(specifications) > 10:
                print(f"\n  ... 还有 {len(specifications) - 10} 个规格")
        
        # 保存结果
        results_file = RESULTS_DIR / f"winco_pagination_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 结果已保存到: {results_file}")
        
        return result['success']
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()

if __name__ == '__main__':
    success = test_winco_pagination()
    print("\n✅ Winco 分页测试完成" if success else "\n❌ Winco 分页测试失败") 