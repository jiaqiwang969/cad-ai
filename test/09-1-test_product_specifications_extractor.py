#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 09-1 —— 产品规格链接提取器 (重新设计版)
一次性加载所有产品规格，无需翻页
运行: make test-09-1
"""
import os, sys, time, re, json
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("❌ Selenium 未安装，无法运行测试！")
    sys.exit(1)

RESULTS_DIR = Path("results/product_specifications")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 默认产品URL（可通过环境变量覆盖）
# 之前的铝型材产品URL
# DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/jlcmc-aluminum-extrusion-txceh161515l100dalka75?Product=90-27122024-029219"
DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/jw-winco-en-561-plastic-mounting-angle-brackets-type-b-and-c?CatalogPath=TRACEPARTS%3ATP05001&Product=90-05102020-040831"
#DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/the-timken-company-double-concentric-cartridge-block-qaamc10a050s?CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175"
#DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/jw-winco-din-787-metric-size-steel-tslot-bolts?CatalogPath=TRACEPARTS%3ATP01001013006&Product=90-04092020-049501"
#DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/the-timken-company-double-concentric-cartridge-block-qaamc10a050s?CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175"
#DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/petzoldt-cpleuchten-gmbh-rohrleuchte-sls50-14w-230v?CatalogPath=TRACEPARTS%3ATP12001003&Product=90-13052019-057778"
PRODUCT_URL = os.getenv("TRACEPARTS_PRODUCT_URL", DEFAULT_PRODUCT_URL)

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

def set_items_per_page_to_all(driver):
    """设置每页显示项目数为全部"""
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
            print("  ℹ️ 未检测到分页控件，可能是单页面，直接提取数据")
            return False  # 返回False表示没有分页，但这是正常情况
            
    except Exception as e:
        print(f"  ⚠️ 检测分页控件时出错: {e}")
        return False
    
    # 策略1: 寻找分页区域中的数字和下拉控件
    try:
        print("  🔍 策略1: 查找分页区域的控件...")
        
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
                                    print(f"    找到分页容器，文本: {container.text[:100]}...")
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
            print("    在分页容器中查找可点击数字...")
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
                        
                        print(f"      找到可点击元素: {elem_tag} '{elem_text}'")
                        
                        # 如果是select，检查选项
                        if elem_tag == 'select':
                            options = elem.find_elements(By.TAG_NAME, 'option')
                            option_texts = [opt.text.strip() for opt in options]
                            print(f"        选项: {option_texts}")
                            
                            # 查找All或大数字选项
                            for opt in options:
                                text = opt.text.strip().lower()
                                if text in ['all', '全部'] or (text.isdigit() and int(text) >= 50):
                                    print(f"        ✅ 选择: {opt.text}")
                                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", opt)
                                    time.sleep(1)
                                    opt.click()
                                    time.sleep(5)
                                    return True
                        
                        # 如果是数字文本且可点击，尝试点击
                        elif elem.is_displayed() and elem.is_enabled():
                            if elem_text.isdigit() or elem_text.lower() in ['all', '全部']:
                                try:
                                    print(f"        🖱️ 尝试点击: {elem_text}")
                                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                                    time.sleep(1)
                                    elem.click()
                                    time.sleep(3)
                                    
                                    # 🎯 关键改进：明确查找并点击"All"选项
                                    print(f"        🔍 查找弹出菜单中的All选项...")
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
                                                    print(f"        ✅ 找到All选项: {all_option.text} ({all_option.tag_name})")
                                                    all_option.click()
                                                    print(f"        ✅ 成功选择All选项！")
                                                    time.sleep(5)
                                                    all_found = True
                                                    return True
                                        except Exception as e:
                                            continue
                                    
                                    if not all_found:
                                        # 如果没找到All，尝试找最大数字
                                        print(f"        🔍 未找到All，查找最大数字选项...")
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
                                                        print(f"        ✅ 选择最大数字: {max_option.text}")
                                                        max_option.click()
                                                        time.sleep(5)
                                                        return True
                                            except:
                                                continue
                                        
                                        print(f"        ⚠️ 点击后未找到合适的选项")
                                    
                                except Exception as e:
                                    print(f"        ❌ 点击失败: {e}")
                                    
                except Exception as e:
                    print(f"      查找元素失败: {e}")
                    
    except Exception as e:
        print(f"  ❌ 策略1失败: {e}")
    
    # 策略2: 更直接的查找方式 - 查找包含当前页数"10"的可点击元素
    try:
        print("  🔍 策略2: 查找当前页数控件...")
        
        # 查找显示"10"的可点击元素 (当前每页显示数量)
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
                        
                        print(f"    找到数字控件: {elem_tag} '{elem_text}' class='{elem_class}'")
                        
                        if elem_tag == 'select':
                            # 如果是select，查找All选项
                            options = elem.find_elements(By.TAG_NAME, 'option')
                            for opt in options:
                                if opt.text.strip().lower() in ['all', '全部'] or (opt.text.strip().isdigit() and int(opt.text.strip()) >= 50):
                                    print(f"    ✅ 在select中选择: {opt.text}")
                                    opt.click()
                                    time.sleep(5)
                                    return True
                        else:
                            # 如果是可点击元素，尝试点击
                            try:
                                print(f"    🖱️ 点击数字控件: {elem_text}")
                                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
                                time.sleep(1)
                                elem.click()
                                time.sleep(3)
                                
                                # 查找弹出菜单中的All选项
                                all_options = driver.find_elements(By.XPATH, "//li[normalize-space(.)='All'] | //option[normalize-space(.)='All'] | //*[@role='option'][normalize-space(.)='All']")
                                for opt in all_options:
                                    if opt.is_displayed():
                                        opt.click()
                                        print(f"    ✅ 选择了All选项")
                                        time.sleep(5)
                                        return True
                                        
                            except Exception as e:
                                print(f"    ❌ 点击数字控件失败: {e}")
                                
            except Exception as e:
                print(f"    查找数字控件失败: {e}")
                
    except Exception as e:
        print(f"  ❌ 策略2失败: {e}")
    
    # 策略3: 查找所有select元素，专门寻找包含数字选项的
    try:
        print("  🔍 策略3: 检查所有select元素...")
        
        select_elements = driver.find_elements(By.TAG_NAME, 'select')
        print(f"    页面共有 {len(select_elements)} 个select元素")
        
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
                
                print(f"    Select {i+1}: 包含数字={has_numbers}")
                if len(option_data) <= 10:  # 只显示选项少的select
                    print(f"      选项: {option_data}")
                
                # 如果包含数字选项，可能是分页控件
                if has_numbers:
                    print(f"    🎯 这可能是分页控件，尝试选择最大值...")
                    
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
                        print(f"      ✅ 选择: {best_option.text}")
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", best_option)
                        time.sleep(1)
                        best_option.click()
                        time.sleep(5)
                        return True
                        
            except Exception as e:
                print(f"    处理select {i+1}失败: {e}")
                
    except Exception as e:
        print(f"  ❌ 策略3失败: {e}")
    
    print("  ❌ 所有策略都未能找到可用的分页控件")
    return False

def extract_all_product_specifications(driver):
    """一次性提取所有产品规格"""
    print("📋 开始提取所有产品规格...")
    
    specifications = []
    seen_references = set()
    
    try:
        # 等待页面稳定
        time.sleep(3)
        
        # 完整滚动页面
        scroll_page_fully(driver)
        
        # 方法1: 查找 "Product selection" 或类似标题下的表格
        print("🔍 查找产品选择区域...")
        
        # 查找产品选择相关的标题
        product_section_keywords = [
            'product selection', 'product list', 'product specifications',
            'available products', 'product variants', 'models available',
            'produktauswahl', 'produktliste', 'produktspezifikationen',  # 德语
            'sélection de produits', 'liste des produits',  # 法语
            '产品选择', '产品列表', '产品规格',  # 中文
            'specification', 'specifications', 'technical data'
        ]
        
        product_section = None
        table_element = None
        
        # 尝试通过标题查找
        for keyword in product_section_keywords:
            # 查找包含关键词的标题元素
            xpath_selectors = [
                f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                f"//h1[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                f"//h2[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                f"//h3[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                f"//h4[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                f"//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]"
            ]
            
            for selector in xpath_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem.text.strip():
                            print(f"  ✅ 找到相关标题: '{elem.text.strip()}'")
                            
                            # 查找该元素后面的第一个表格
                            # 先尝试在同一父容器内查找
                            parent = elem.find_element(By.XPATH, "./..")
                            tables = parent.find_elements(By.TAG_NAME, 'table')
                            
                            if not tables:
                                # 尝试在后续兄弟元素中查找
                                tables = elem.find_elements(By.XPATH, "./following-sibling::*//table")
                            
                            if not tables:
                                # 尝试在整个文档中查找该元素之后的表格
                                tables = elem.find_elements(By.XPATH, "./following::table")
                            
                            if tables:
                                table_element = tables[0]
                                product_section = elem
                                print(f"  ✅ 在 '{elem.text.strip()}' 下找到表格")
                                break
                                
                except Exception as e:
                    continue
                    
                if table_element:
                    break
            
            if table_element:
                break
        
        # 如果没有找到，使用原方法查找最大的表格
        if not table_element:
            print("  ⚠️ 未找到产品选择区域，尝试查找最大的表格...")
            tables = driver.find_elements(By.TAG_NAME, 'table')
            
            if not tables:
                print("❌ 未找到任何表格")
                return specifications
            
            # 选择最大的表格
            table_element = max(tables, key=lambda t: len(t.find_elements(By.TAG_NAME, 'tr')))
        
        # 分析找到的表格
        rows = table_element.find_elements(By.TAG_NAME, 'tr')
        print(f"📊 分析表格，共 {len(rows)} 行")
        
        # 检测表格类型
        is_vertical_table = False
        
        # 检查前几行是否都是2列格式
        two_col_count = 0
        for i, row in enumerate(rows[:5]):  # 检查前5行
            cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
            if len(cells) == 2:
                two_col_count += 1
        
        if two_col_count >= 3:  # 如果至少3行都是2列，可能是纵向表格
            is_vertical_table = True
            print("  🔄 检测到纵向表格格式（属性-值对）")
        
        # 提取所有可能的产品编号
        if is_vertical_table:
            # 纵向表格：提取所有值，检查哪些可能是产品编号
            print("  🔍 从纵向表格提取数据...")
            for i, row in enumerate(rows):
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                if len(cells) != 2:
                    continue
                
                prop_name = cells[0].text.strip()
                prop_value = cells[1].text.strip()
                
                # 显示所有属性-值对
                print(f"    行 {i+1}: '{prop_name}' => '{prop_value}'")
                
                # 检查值是否可能是产品编号（使用更智能的判断）
                if prop_value and len(prop_value) >= 3 and prop_value not in seen_references:
                    # 智能判断：如果看起来像编号（包含数字或特殊格式）
                    if is_likely_product_reference(prop_value):
                        spec_info = {
                            'reference': prop_value,
                            'row_index': i,
                            'dimensions': '',
                            'weight': '',
                            'property_name': prop_name,
                            'table_type': 'vertical'
                        }
                        
                        specifications.append(spec_info)
                        seen_references.add(prop_value)
                        print(f"  📦 提取规格: {prop_value} (来自: {prop_name})")
        
        else:
            # 横向表格
            print("  📊 检测到横向表格格式")
            
            # 查找表头行
            header_row_index = -1
            header_cells = []
            
            for i, row in enumerate(rows):
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                if not cells:
                    continue
                
                # 如果是th元素，很可能是表头
                th_cells = row.find_elements(By.TAG_NAME, 'th')
                if th_cells and len(th_cells) == len(cells):
                    header_row_index = i
                    header_cells = [cell.text.strip() for cell in cells]
                    print(f"  📋 识别表头行 {i+1}: {header_cells[:5]}...")
                    break
            
            # 确定产品编号列（根据列名）
            product_columns = []
            if header_cells:
                for j, header in enumerate(header_cells):
                    header_lower = header.lower()
                    
                    # 匹配各种语言的产品编号列名
                    if any(keyword in header_lower for keyword in [
                        'part number', 'part no', 'part#', 'p/n',
                        'product number', 'product code', 'product id',
                        'model', 'model number', 'model no',
                        'reference', 'ref', 'item number', 'item no',
                        'catalog number', 'cat no', 'sku',
                        'bestellnummer', 'artikelnummer', 'teilenummer',  # 德语
                        'numéro', 'référence',  # 法语
                        'número', 'codigo',  # 西班牙语
                        '型号', '编号', '料号'  # 中文
                    ]):
                        product_columns.append(j)
                        print(f"    ✓ 识别产品编号列 {j+1}: '{header}'")
                        
                # 通用简化逻辑：只使用第一个产品编号列
                if len(product_columns) > 1:
                    print(f"    ℹ️ 发现 {len(product_columns)} 个产品编号列，只使用第一个主要列")
                    product_columns = product_columns[:1]
            
            # 如果没有识别到产品编号列，使用智能判断
            if not product_columns:
                print("    ⚠️ 未识别到明确的产品编号列，将使用智能判断")
                use_smart_detection = True
            else:
                use_smart_detection = False
            
            # 提取数据行
            for i, row in enumerate(rows):
                if i <= header_row_index:  # 跳过表头及之前的行
                    continue
                    
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                if not cells:
                    continue
                
                cell_texts = [cell.text.strip() for cell in cells]
                
                # 查找可能的产品编号
                if use_smart_detection:
                    # 智能检测模式：扫描所有单元格
                    for j, cell_text in enumerate(cell_texts):
                        if cell_text and len(cell_text) >= 3 and cell_text not in seen_references:
                            if is_likely_product_reference(cell_text):
                                spec_info = {
                                    'reference': cell_text,
                                    'row_index': i,
                                    'column_index': j,
                                    'dimensions': extract_dimensions_from_cells(cell_texts),
                                    'weight': extract_weight_from_cells(cell_texts),
                                    'all_cells': cell_texts,
                                    'table_type': 'horizontal'
                                }
                                
                                # 如果有表头，添加列名信息
                                if header_cells and j < len(header_cells):
                                    spec_info['column_name'] = header_cells[j]
                                
                                specifications.append(spec_info)
                                seen_references.add(cell_text)
                                
                                if len(specifications) <= 10:
                                    print(f"  📦 提取规格 {len(specifications)}: {cell_text}")
                                
                                # 在智能模式下，每行只取第一个符合条件的
                                break
                else:
                    # 使用识别的产品编号列
                    for col_idx in product_columns:
                        if col_idx < len(cell_texts):
                            cell_text = cell_texts[col_idx]
                            if cell_text and len(cell_text) >= 3 and cell_text not in seen_references:
                                # 对产品编号列的内容，放宽验证
                                if cell_text and not cell_text.lower() in ['', 'n/a', 'na', '-', '/', 'none']:
                                    spec_info = {
                                        'reference': cell_text,
                                        'row_index': i,
                                        'column_index': col_idx,
                                        'dimensions': extract_dimensions_from_cells(cell_texts),
                                        'weight': extract_weight_from_cells(cell_texts),
                                        'all_cells': cell_texts,
                                        'table_type': 'horizontal'
                                    }
                                    
                                    # 添加列名信息
                                    if header_cells and col_idx < len(header_cells):
                                        spec_info['column_name'] = header_cells[col_idx]
                                    
                                    specifications.append(spec_info)
                                    seen_references.add(cell_text)
                                    
                                    if len(specifications) <= 10:
                                        print(f"  📦 提取规格 {len(specifications)}: {cell_text}")
        
        if len(specifications) > 10:
            print(f"  ... 还有 {len(specifications) - 10} 个规格")
            
    except Exception as e:
        print(f"❌ 提取规格时出错: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"✅ 总共提取到 {len(specifications)} 个产品规格")
    return specifications

def is_likely_product_reference(text):
    """智能判断文本是否可能是产品编号"""
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

def is_valid_product_reference_relaxed(text):
    """判断文本是否是有效的产品编号 - 放宽版（用于纵向表格）"""
    # 直接使用新的智能判断函数
    return is_likely_product_reference(text)

def is_valid_product_reference(text):
    """判断文本是否是有效的产品编号 - 改进版"""
    # 直接使用新的智能判断函数
    return is_likely_product_reference(text)

def extract_dimensions_from_cells(cells):
    """从单元格中提取尺寸信息"""
    for cell_text in cells:
        dimension_match = re.search(r'\d+x\d+x?\d*', cell_text)
        if dimension_match:
            return dimension_match.group()
    return ''

def extract_weight_from_cells(cells):
    """从单元格中提取重量或长度信息"""
    for cell_text in cells:
        measure_match = re.search(r'(\d+[,\.]\d+|\d+)\s*(mm|kg|m|cm)', cell_text.lower())
        if measure_match:
            return measure_match.group()
    return ''

def extract_base_product_info(product_url):
    """从产品URL中提取基础信息"""
    try:
        parsed_url = urlparse(product_url)
        path_parts = parsed_url.path.split('/')
        
        # 获取基础产品名称
        base_product_name = path_parts[-1] if path_parts else "unknown-product"
        
        # 解析查询参数
        query_params = parse_qs(parsed_url.query)
        product_id = query_params.get('Product', ['unknown-id'])[0]
        catalog_path = query_params.get('CatalogPath', ['unknown-catalog'])[0] if 'CatalogPath' in query_params else 'unknown-catalog'
        
        return {
            'base_url': f"{parsed_url.scheme}://{parsed_url.netloc}",
            'base_path': parsed_url.path,
            'base_product_name': base_product_name,
            'product_id': product_id,
            'catalog_path': catalog_path,
            'query_params': query_params
        }
    except Exception as e:
        print(f"⚠️ 解析产品URL失败: {e}")
        return None

def generate_specification_urls(base_info, specifications):
    """根据基础信息和规格生成特定的产品URL"""
    print("🔗 生成规格专用链接...")
    
    if not base_info:
        print("❌ 缺少基础产品信息")
        return []
    
    spec_urls = []
    
    for spec in specifications:
        try:
            reference = spec.get('reference', '')
            if not reference:
                continue
            
            # 构建查询参数
            query_params = base_info['query_params'].copy()
            query_params['PartNumber'] = [reference]
            
            # 重新编码查询字符串
            query_string = urlencode(query_params, doseq=True)
            
            # 构建完整URL
            spec_url = f"{base_info['base_url']}{base_info['base_path']}?{query_string}"
            
            spec_url_info = {
                'reference': reference,
                'dimensions': spec.get('dimensions', ''),
                'weight': spec.get('weight', ''),
                'url': spec_url,
                'original_spec_data': spec
            }
            
            spec_urls.append(spec_url_info)
            
        except Exception as e:
            print(f"⚠️ 生成规格URL时出错 ({reference}): {e}")
    
    print(f"  ✅ 成功生成 {len(spec_urls)} 个规格链接")
    return spec_urls

def save_results(base_info, specifications, spec_urls):
    """保存提取结果"""
    timestamp = int(time.time())
    
    # 🎯 改进的JSON格式
    results = {
        'extraction_info': {
            'timestamp': timestamp,
            'extraction_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'base_product_url': PRODUCT_URL,
            'total_specifications_found': len(specifications),
            'total_urls_generated': len(spec_urls)
        },
        'base_product_info': base_info,
        'product_specifications': specifications,
        'specification_urls': spec_urls,
        'summary': {
            'series_distribution': {},
            'specification_samples': []
        }
    }
    
    # 分析产品系列分布
    series_stats = {}
    for spec in specifications:
        ref = spec.get('reference', '')
        if ref:
            # 尝试提取产品系列，适配不同格式
            series_patterns = [
                r'(TXCE-[A-Z0-9]+-[0-9]+-[0-9]+)',  # TXCE系列
                r'([A-Z]{2,4}-[0-9]+)',              # EN-561类型
                r'([A-Z]+[0-9]+)',                   # 简单字母数字组合
                r'([A-Z]+-[A-Z0-9]+)'               # 通用格式
            ]
            
            series = ref  # 默认使用完整编号
            for pattern in series_patterns:
                match = re.match(pattern, ref)
                if match:
                    series = match.group(1)
                    break
            
            if series not in series_stats:
                series_stats[series] = 0
            series_stats[series] += 1
    
    results['summary']['series_distribution'] = series_stats
    
    # 添加规格样本（前10个）
    for i, spec in enumerate(specifications[:10]):
        sample = {
            'index': i + 1,
            'reference': spec.get('reference', ''),
            'dimensions': spec.get('dimensions', ''),
            'weight': spec.get('weight', ''),
            'url': spec_urls[i]['url'] if i < len(spec_urls) else ''
        }
        results['summary']['specification_samples'].append(sample)
    
    # 🎯 获取当前工作目录，生成完整路径
    import os
    current_dir = os.getcwd()
    
    # 保存详细JSON结果
    json_file = RESULTS_DIR / f"product_specs_complete_{timestamp}.json"
    json_full_path = os.path.join(current_dir, json_file)
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"💾 完整结果已保存到: {json_full_path}")
    
    # 保存简化的规格列表JSON
    simple_specs = []
    for i, spec in enumerate(specifications):
        simple_spec = {
            'id': i + 1,
            'reference': spec.get('reference', ''),
            'dimensions': spec.get('dimensions', ''),
            'weight': spec.get('weight', ''),
            'series': '',
            'url': spec_urls[i]['url'] if i < len(spec_urls) else ''
        }
        
        # 提取系列信息，适配不同格式
        ref = spec.get('reference', '')
        if ref:
            for pattern in [
                r'(TXCE-[A-Z0-9]+-[0-9]+-[0-9]+)',
                r'([A-Z]{2,4}-[0-9]+)',
                r'([A-Z]+[0-9]+)',
                r'([A-Z]+-[A-Z0-9]+)'
            ]:
                match = re.match(pattern, ref)
                if match:
                    simple_spec['series'] = match.group(1)
                    break
            if not simple_spec['series']:
                simple_spec['series'] = ref
        
        simple_specs.append(simple_spec)
    
    simple_json_file = RESULTS_DIR / f"specs_list_{timestamp}.json"
    simple_json_full_path = os.path.join(current_dir, simple_json_file)
    with open(simple_json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'extraction_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_count': len(simple_specs),
            'specifications': simple_specs
        }, f, indent=2, ensure_ascii=False)
    print(f"📋 简化规格列表已保存到: {simple_json_full_path}")
    
    # 保存简化的URL列表
    urls_file = RESULTS_DIR / f"spec_urls_{timestamp}.txt"
    urls_full_path = os.path.join(current_dir, urls_file)
    with open(urls_file, 'w', encoding='utf-8') as f:
        f.write(f"# 产品规格链接列表\n")
        f.write(f"# 基础产品: {PRODUCT_URL}\n")
        f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 找到 {len(spec_urls)} 个规格\n\n")
        
        for spec_url_info in spec_urls:
            f.write(f"# {spec_url_info['reference']} ({spec_url_info['dimensions']})\n")
            f.write(f"{spec_url_info['url']}\n\n")
    
    print(f"📄 URL列表已保存到: {urls_full_path}")
    
    # 输出结果摘要
    print("\n" + "="*80)
    print("📋 提取结果摘要")
    print("="*80)
    print(f"基础产品URL: {PRODUCT_URL}")
    print(f"找到规格数量: {len(specifications)}")
    print(f"生成链接数量: {len(spec_urls)}")
    
    if series_stats:
        print(f"\n📊 产品系列分布:")
        for series, count in sorted(series_stats.items()):
            print(f"  {series}: {count} 个规格")
    
    print("\n🔗 规格链接列表 (显示前10个):")
    for i, spec_url_info in enumerate(spec_urls[:10], 1):
        print(f"{i:2d}. {spec_url_info['reference']} ({spec_url_info['dimensions']})")
        print(f"    {spec_url_info['url']}")
    if len(spec_urls) > 10:
        print(f"... 还有 {len(spec_urls) - 10} 个链接")
    
    print(f"\n💾 生成文件完整路径:")
    print(f"  📋 完整JSON: {json_full_path}")
    print(f"  📋 简化JSON: {simple_json_full_path}")
    print(f"  📄 URL列表: {urls_full_path}")
    print("="*80)

def main():
    print("🎯 产品规格链接提取器 (重新设计版)")
    print(f"📍 目标产品: {PRODUCT_URL}")
    print("🔄 策略: 一次性加载所有数据，无翻页")
    
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium 未安装，无法运行！")
        return False
    
    # 提取基础产品信息
    base_info = extract_base_product_info(PRODUCT_URL)
    if not base_info:
        print("❌ 无法解析基础产品信息")
        return False
    
    print(f"📦 产品ID: {base_info['product_id']}")
    
    driver = prepare_driver()
    
    try:
        # 访问产品页面
        print(f"🌐 访问产品页面...")
        driver.get(PRODUCT_URL)
        time.sleep(3)
        
        # 截图保存初始状态
        screenshot_path = RESULTS_DIR / f"initial_page_{int(time.time())}.png"
        driver.save_screenshot(str(screenshot_path))
        print(f"📸 初始页面截图: {screenshot_path}")
        
        # 尝试设置每页显示为全部
        items_per_page_success = set_items_per_page_to_all(driver)
        
        if items_per_page_success:
            print("✅ 成功设置显示全部项目")
            # 再次截图确认
            final_screenshot = RESULTS_DIR / f"after_show_all_{int(time.time())}.png"
            driver.save_screenshot(str(final_screenshot))
            print(f"📸 设置后截图: {final_screenshot}")
        else:
            print("ℹ️ 单页面模式：直接提取当前页面数据")
        
        # 确保页面完全加载
        scroll_page_fully(driver)
        
        # 提取所有规格信息
        specifications = extract_all_product_specifications(driver)
        
        if not specifications:
            print("❌ 未找到任何产品规格")
            return False
        
        # 生成规格URL
        spec_urls = generate_specification_urls(base_info, specifications)
        
        if not spec_urls:
            print("❌ 未能生成任何规格URL")
            return False
        
        # 保存结果
        save_results(base_info, specifications, spec_urls)
        
        print("✅ 规格链接提取完成！")
        return True
        
    except Exception as e:
        print(f"❌ 提取过程中发生错误: {e}")
        return False
    finally:
        driver.quit()

if __name__ == '__main__':
    success = main()
    print("✅ test-09-1 成功" if success else "❌ test-09-1 失败") 