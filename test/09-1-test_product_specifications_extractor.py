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

# === NEW: 全局打印时间戳 ===
import builtins as _bt
_orig_print = _bt.print

def _ts_print(*args, **kwargs):
    _orig_print(f"[{time.strftime('%H:%M:%S')}]", *args, **kwargs)

_bt.print = _ts_print

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
#DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/jw-winco-en-561-plastic-mounting-angle-brackets-type-b-and-c?CatalogPath=TRACEPARTS%3ATP05001&Product=90-05102020-040831"
# 轴承单元产品
DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/ntn-europe-usc200t20-cartridge-unit-from-grey-cast-high-temperature?CatalogPath=TRACEPARTS%3ATP01002002006&Product=34-17112021-055894"
# 太阳能温室产品
#DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/chiari-bruno-srl-serramenti-solar-greenhouse-with-curtain-2m?CatalogPath=TRACEPARTS%3ATP12001002&Product=90-09062022-058238"

#DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/the-timken-company-double-concentric-cartridge-block-qaamc10a050s?CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175"
#DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/jw-winco-din-787-metric-size-steel-tslot-bolts?CatalogPath=TRACEPARTS%3ATP01001013006&Product=90-04092020-049501"
#DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/the-timken-company-double-concentric-cartridge-block-qaamc10a050s?CatalogPath=TRACEPARTS%3ATP01002002006&Product=90-31032023-039175"
#DEFAULT_PRODUCT_URL = "https://www.traceparts.cn/en/product/petzoldt-cpleuchten-gmbh-rohrleuchte-sls50-14w-230v?CatalogPath=TRACEPARTS%3ATP12001003&Product=90-13052019-057778"
PRODUCT_URL = os.getenv("TRACEPARTS_PRODUCT_URL", DEFAULT_PRODUCT_URL)

FAST_MODE = os.getenv("FAST_MODE", "0") == "1"
DEBUG_MODE = os.getenv("DEBUG", "1") == "1"

# 记录已处理弹窗的域，避免重复等待
_POPUP_HANDLED_DOMAINS = set()

def prepare_driver():
    """准备Chrome驱动器"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 若启用FAST_MODE，禁用图片和字体加载
    if FAST_MODE:
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.fonts": 2,
        }
        options.add_experimental_option("prefs", prefs)
        print("⚡ FAST_MODE: 已禁用图片/字体加载")
    
    # FAST_MODE 时添加额外的优化设置
    if FAST_MODE:
        try:
            # 添加性能优化设置
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-dev-shm-usage")
        except Exception as e:
            print(f"  ⚠️ 配置FAST_MODE优化设置时出错: {e}")
            
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(40)
    return driver

def scroll_page_fully(driver):
    """完整滚动页面确保所有内容加载"""
    print("🔄 滚动页面确保内容完全加载...")
    
    if FAST_MODE:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.3)
    else:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)

def set_items_per_page_to_all(driver):
    """设置每页显示项目数为全部"""
    if not DEBUG_MODE:
        print("🎯 设置分页...")
    else:
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
                                    # 等待页面刷新而非固定等待
                                    try:
                                        WebDriverWait(driver, 5).until(
                                            lambda d: "All" in d.find_element(By.XPATH, "//button[text()='10' or text()='All']").text
                                            or len(d.find_elements(By.TAG_NAME, 'tr')) > 15
                                        )
                                    except:
                                        time.sleep(2 if FAST_MODE else 5)
                                    print(f"        ✅ 成功选择All选项！")
                                    all_found = True
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
                                                    # 等待页面刷新而非固定等待
                                                    try:
                                                        WebDriverWait(driver, 5).until(
                                                            lambda d: "All" in d.find_element(By.XPATH, "//button[text()='10' or text()='All']").text
                                                            or len(d.find_elements(By.TAG_NAME, 'tr')) > 15
                                                        )
                                                    except:
                                                        time.sleep(2 if FAST_MODE else 5)
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
                                                        time.sleep(2 if FAST_MODE else 5)
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
                                    time.sleep(2 if FAST_MODE else 5)
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
                                        time.sleep(2 if FAST_MODE else 5)
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
                        time.sleep(2 if FAST_MODE else 5)
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
        time.sleep(1 if FAST_MODE else 3)
        
        # 检查是否已处理过弹窗
        current_domain = driver.current_url.split('/')[2]
        skip_popup_check = current_domain in _POPUP_HANDLED_DOMAINS
        
        if not skip_popup_check:
            # 🔧 NEW: 处理许可协议弹窗
            if DEBUG_MODE:
                print("🔧 [NEW] 检测并处理许可协议弹窗...")
            
            # 查找可能的弹窗和确认按钮
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
                            if DEBUG_MODE:
                                print(f"🔧 [NEW] 发现弹窗元素: '{popup_text}'")
                            popup_found = True
                            break
                    if popup_found:
                        break
                except Exception as e:
                    continue
            
            if popup_found:
                if DEBUG_MODE:
                    print("🔧 [NEW] 检测到弹窗，查找确认按钮...")
                
                # 查找确认按钮的多种可能文本
                confirm_button_texts = [
                    # 英文
                    'i understand and accept',
                    'i understand', 
                    'accept',
                    'agree',
                    'continue', 'ok'
                ]
                
                confirm_clicked = False
                
                for button_text in confirm_button_texts:
                    if confirm_clicked:
                        break
                        
                    print(f"🔧 [NEW] 搜索确认按钮: '{button_text}'")
                    
                    # 多种按钮选择器
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
                                    if DEBUG_MODE:
                                        print(f"🔧 [NEW] 找到确认按钮: '{button_full_text}'")
                                    
                                    # 尝试点击按钮
                                    try:
                                        # 滚动到按钮位置
                                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
                                        time.sleep(0.5 if FAST_MODE else 1)
                                        
                                        # 点击按钮
                                        button.click()
                                        if DEBUG_MODE:
                                            print(f"🔧 [NEW] ✅ 成功点击确认按钮!")
                                        confirm_clicked = True
                                        
                                        # 等待弹窗消失 (FAST_MODE 用显式等待)
                                        try:
                                            WebDriverWait(driver, 3).until(lambda d: not button.is_displayed())
                                        except Exception:
                                            time.sleep(1 if FAST_MODE else 3)
                                        
                                        # 记录已处理
                                        _POPUP_HANDLED_DOMAINS.add(current_domain)
                                        
                                        # 检查弹窗是否消失
                                        if DEBUG_MODE:
                                            try:
                                                if not button.is_displayed():
                                                    print("🔧 [NEW] ✅ 弹窗已消失")
                                                else:
                                                    print("🔧 [NEW] ⚠️ 弹窗可能仍然存在")
                                            except:
                                                print("🔧 [NEW] ✅ 按钮元素已移除，弹窗应已关闭")
                                        
                                        break
                                        
                                    except Exception as e:
                                        print(f"🔧 [NEW] ❌ 点击按钮失败: {e}")
                                        # 尝试JavaScript点击
                                        try:
                                            driver.execute_script("arguments[0].click();", button)
                                            print(f"🔧 [NEW] ✅ JavaScript点击成功!")
                                            confirm_clicked = True
                                            time.sleep(3)
                                            break
                                        except Exception as e2:
                                            print(f"🔧 [NEW] ❌ JavaScript点击也失败: {e2}")
                        
                            if confirm_clicked:
                                break
                                
                        except Exception as e:
                            continue
                
                if not confirm_clicked:
                    print("🔧 [NEW] ⚠️ 未找到可点击的确认按钮，尝试通用方法...")
                    
                    # 最后尝试：查找所有可见的按钮并尝试点击
                    try:
                        all_buttons = driver.find_elements(By.CSS_SELECTOR, "button, input[type='button'], input[type='submit'], a[role='button'], .btn, .button")
                        for button in all_buttons:
                            if button.is_displayed() and button.is_enabled():
                                button_text = button.text.strip().lower()
                                button_value = (button.get_attribute('value') or '').strip().lower()
                                
                                # 检查是否包含确认相关的关键词
                                confirm_keywords = ['accept', 'agree', 'understand', 'continue', 'ok', 'confirm', 'proceed']
                                if any(keyword in button_text or keyword in button_value for keyword in confirm_keywords):
                                    print(f"🔧 [NEW] 尝试通用按钮: '{button.text.strip()}'")
                                    try:
                                        button.click()
                                        print(f"🔧 [NEW] ✅ 通用按钮点击成功!")
                                        time.sleep(3)
                                        confirm_clicked = True
                                        break
                                    except:
                                        continue
                    except Exception as e:
                        print(f"🔧 [NEW] 通用方法失败: {e}")
                
                if confirm_clicked:
                    if DEBUG_MODE:
                        print("🔧 [NEW] ✅ 许可协议已确认，等待页面重新加载...")
                    # 动态等待表格出现
                    try:
                        WebDriverWait(driver, 5).until(
                            lambda d: any(t.is_displayed() for t in d.find_elements(By.TAG_NAME, 'table'))
                        )
                    except:
                        time.sleep(2 if FAST_MODE else 5)
                else:
                    if DEBUG_MODE:
                        print("🔧 [NEW] ❌ 无法处理许可协议弹窗")
            else:
                if DEBUG_MODE:
                    print(f"🔧 [NEW] 跳过弹窗检测（域名 {current_domain} 已处理）")
        
        # 完整滚动页面
        scroll_page_fully(driver)
        
        # 🐛 DEBUG: 保存完整的HTML源码
        if DEBUG_MODE and not FAST_MODE:
            print("🐛 [DEBUG] 保存页面HTML源码用于分析...")
            timestamp = int(time.time())
            html_file = RESULTS_DIR / f"page_source_debug_{timestamp}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"🐛 [DEBUG] HTML源码已保存到: {html_file}")
        else:
            timestamp = int(time.time())
        
        # 🐛 DEBUG: 分析页面基本信息
        if DEBUG_MODE:
            print("🐛 [DEBUG] 页面基本信息分析...")
            page_title = driver.title
            page_url = driver.current_url
            print(f"🐛 [DEBUG] 页面标题: {page_title}")
            print(f"🐛 [DEBUG] 当前URL: {page_url}")
        
        # 🐛 DEBUG: 统计页面元素
        if DEBUG_MODE:
            all_tables = driver.find_elements(By.TAG_NAME, 'table')
            all_divs = driver.find_elements(By.TAG_NAME, 'div')
            all_headers = driver.find_elements(By.CSS_SELECTOR, 'h1, h2, h3, h4, h5, h6')
            print(f"🐛 [DEBUG] 页面统计: {len(all_tables)} 个表格, {len(all_divs)} 个div, {len(all_headers)} 个标题")
        else:
            all_tables = driver.find_elements(By.TAG_NAME, 'table')
        
        # 🔧 NEW: 检测动态内容加载情况
        print("🔧 [NEW] 检测动态内容加载...")
        
        # 查找分页信息，判断是否需要等待动态加载
        pagination_indicators = [
            "items per page", "out of", "total", "results", "showing"
        ]
        
        has_pagination_text = False
        visible_tables_count = len([t for t in all_tables if t.is_displayed()])
        
        for indicator in pagination_indicators:
            elements = driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{indicator}')]")
            for elem in elements:
                if elem.is_displayed() and elem.text.strip():
                    has_pagination_text = True
                    print(f"🔧 [NEW] 发现分页信息: '{elem.text.strip()}'")
                    break
            if has_pagination_text:
                break
        
        print(f"🔧 [NEW] 分页文本存在: {has_pagination_text}, 可见表格数: {visible_tables_count}")
        
        # 🔧 NEW: 如果有分页文本但没有可见的有效表格，尝试动态加载策略
        if has_pagination_text and visible_tables_count == 0:
            if not FAST_MODE:  # FAST_MODE下跳过复杂的动态加载策略
                print("🔧 [NEW] 检测到动态内容加载问题，执行特殊策略...")
                
                # 策略1: 等待更长时间
                print("🔧 [NEW] 策略1: 延长等待时间...")
                time.sleep(10)
                
                # 策略2: 强制刷新页面
                print("🔧 [NEW] 策略2: 刷新页面...")
                driver.refresh()
                time.sleep(8)
                
                # 策略3: 多次滚动触发懒加载
                print("🔧 [NEW] 策略3: 多次滚动触发内容加载...")
                for i in range(5):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(2)
            
            # 策略4: 尝试点击可能的加载触发器
            print("🔧 [NEW] 策略4: 查找并点击可能的加载触发器...")
            
            # 查找可能需要点击的元素
            clickable_selectors = [
                "//button[contains(text(), 'Load')]",
                "//button[contains(text(), 'Show')]", 
                "//a[contains(text(), 'Load')]",
                "//a[contains(text(), 'Show')]",
                "//*[@class='pagination']//a",
                "//*[contains(@class, 'load-more')]",
                "//*[contains(@class, 'show-all')]"
            ]
            
            for selector in clickable_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            print(f"🔧 [NEW] 尝试点击: {elem.text.strip()}")
                            elem.click()
                            time.sleep(5)
                            break
                except Exception as e:
                    continue
            
            # 策略5: 等待特定元素出现
            print("🔧 [NEW] 策略5: 等待产品数据元素出现...")
            try:
                # 等待包含产品编号的元素出现
                WebDriverWait(driver, 15).until(
                    lambda d: any(
                        t.is_displayed() and len(t.find_elements(By.TAG_NAME, 'tr')) > 1
                        for t in d.find_elements(By.TAG_NAME, 'table')
                    )
                )
                print("🔧 [NEW] ✅ 检测到表格内容已加载")
            except TimeoutException:
                print("🔧 [NEW] ⚠️ 超时：未检测到表格内容加载")
            
            # 策略6: 最终滚动和等待
            scroll_page_fully(driver)
            time.sleep(5)
            
            # 重新获取表格统计
            all_tables = driver.find_elements(By.TAG_NAME, 'table')
            visible_tables_count = len([t for t in all_tables if t.is_displayed()])
            print(f"🔧 [NEW] 动态加载后: {len(all_tables)} 个表格, {visible_tables_count} 个可见")
            
            # 保存处理后的HTML源码
            html_file_after = RESULTS_DIR / f"page_source_after_dynamic_{timestamp}.html"
            with open(html_file_after, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"🔧 [NEW] 处理后HTML源码: {html_file_after}")
        
        # 🐛 DEBUG: 详细分析所有表格
        if DEBUG_MODE:
            print("🐛 [DEBUG] === 所有表格详细分析 ===")
        all_tables = driver.find_elements(By.TAG_NAME, 'table')  # 重新获取
        for i, table in enumerate(all_tables):
            try:
                table_visible = table.is_displayed()
                table_rows = table.find_elements(By.TAG_NAME, 'tr')
                table_cells_total = len(table.find_elements(By.CSS_SELECTOR, 'td, th'))
                
                if DEBUG_MODE:
                    print(f"🐛 [DEBUG] 表格 {i+1}: 可见={table_visible}, {len(table_rows)}行, {table_cells_total}个单元格")
                
                # 如果表格可见且有内容，显示前几行
                if table_visible and len(table_rows) > 0:
                    print(f"🐛 [DEBUG] 表格 {i+1} 内容预览 (前5行):")
                    for j, row in enumerate(table_rows[:5]):
                        cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                        cell_texts = [cell.text.strip() for cell in cells]
                        # 截断过长的文本
                        cell_texts_short = [text[:30] + "..." if len(text) > 30 else text for text in cell_texts]
                        print(f"🐛 [DEBUG]   行 {j+1}: {cell_texts_short}")
                        
                        # 检查是否有链接或特殊属性
                        for k, cell in enumerate(cells):
                            links = cell.find_elements(By.TAG_NAME, 'a')
                            if links:
                                print(f"🐛 [DEBUG]     单元格 {k+1} 包含 {len(links)} 个链接")
                    print("🐛 [DEBUG] ---")
                else:
                    print(f"🐛 [DEBUG]   表格 {i+1} 不可见或无内容")
            except Exception as e:
                print(f"🐛 [DEBUG]   分析表格 {i+1} 时出错: {e}")
        
        # 🐛 DEBUG: 查找所有可能包含产品信息的元素
        if DEBUG_MODE:
            print("🐛 [DEBUG] === 查找产品相关元素 ===")
        
        # 查找包含"part number", "product", "specification"等关键词的元素
        product_keywords = [
            'part number', 'part no', 'product', 'specification', 'model',
            'reference', 'item', 'catalog', 'selection', 'available'
        ]
        
        if DEBUG_MODE:
            for keyword in product_keywords:
                try:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]")
                    visible_elements = [elem for elem in elements if elem.is_displayed() and elem.text.strip()]
                    
                    print(f"🐛 [DEBUG] 关键词 '{keyword}': 找到 {len(visible_elements)} 个可见元素")
                    for i, elem in enumerate(visible_elements[:3]):  # 只显示前3个
                        elem_text = elem.text.strip()[:100] + "..." if len(elem.text.strip()) > 100 else elem.text.strip()
                        elem_tag = elem.tag_name
                        elem_class = elem.get_attribute('class') or 'no-class'
                        print(f"🐛 [DEBUG]   {i+1}. {elem_tag}.{elem_class}: '{elem_text}'")
                except Exception as e:
                    print(f"🐛 [DEBUG] 查找关键词 '{keyword}' 时出错: {e}")
        
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
        
        # 🐛 DEBUG: 详细分析标题查找过程
        if DEBUG_MODE:
            print("🐛 [DEBUG] === 标题查找详细过程 ===")
        
        # 尝试通过标题查找
        for keyword in product_section_keywords:
            print(f"🐛 [DEBUG] 搜索关键词: '{keyword}'")
            
            # 查找包含关键词的标题元素
            xpath_selectors = [
                f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                f"//h1[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                f"//h2[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                f"//h3[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                f"//h4[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]",
                f"//div[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword.lower()}')]"
            ]
            
            for selector_idx, selector in enumerate(xpath_selectors):
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    print(f"🐛 [DEBUG]   选择器 {selector_idx+1}: 找到 {len(elements)} 个元素")
                    
                    for elem_idx, elem in enumerate(elements):
                        if elem.is_displayed() and elem.text.strip():
                            elem_text = elem.text.strip()
                            elem_text_short = elem_text[:200] + "..." if len(elem_text) > 200 else elem_text
                            print(f"🐛 [DEBUG]     元素 {elem_idx+1}: '{elem_text_short}'")
                            print(f"🐛 [DEBUG]     元素标签: {elem.tag_name}, 类名: {elem.get_attribute('class')}")
                            
                            # 🐛 DEBUG: 详细分析这个元素附近的表格
                            print(f"🐛 [DEBUG]     查找该元素附近的表格...")
                            
                            # 查找该元素后面的第一个表格
                            # 先尝试在同一父容器内查找
                            try:
                                parent = elem.find_element(By.XPATH, "./..")
                                tables_in_parent = parent.find_elements(By.TAG_NAME, 'table')
                                print(f"🐛 [DEBUG]       父容器内找到 {len(tables_in_parent)} 个表格")
                                
                                if not tables_in_parent:
                                    # 尝试在后续兄弟元素中查找
                                    tables_siblings = elem.find_elements(By.XPATH, "./following-sibling::*//table")
                                    print(f"🐛 [DEBUG]       后续兄弟元素中找到 {len(tables_siblings)} 个表格")
                                    tables_in_parent = tables_siblings
                                
                                if not tables_in_parent:
                                    # 尝试在整个文档中查找该元素之后的表格
                                    tables_following = elem.find_elements(By.XPATH, "./following::table")
                                    print(f"🐛 [DEBUG]       文档后续位置找到 {len(tables_following)} 个表格")
                                    tables_in_parent = tables_following
                                
                                if tables_in_parent:
                                    candidate_table = tables_in_parent[0]
                                    candidate_rows = candidate_table.find_elements(By.TAG_NAME, 'tr')
                                    print(f"🐛 [DEBUG]       候选表格有 {len(candidate_rows)} 行")
                                    
                                    # 检查表格是否真的包含产品数据
                                    has_meaningful_data = False
                                    for row_idx, row in enumerate(candidate_rows[:3]):  # 检查前3行
                                        cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                                        cell_texts = [cell.text.strip() for cell in cells]
                                        print(f"🐛 [DEBUG]         行 {row_idx+1}: {cell_texts}")
                                        
                                        # 检查是否有非空且有意义的内容
                                        non_empty_cells = [text for text in cell_texts if text and len(text) > 1]
                                        if len(non_empty_cells) >= 2:  # 至少有2个非空单元格
                                            has_meaningful_data = True
                                    
                                    print(f"🐛 [DEBUG]       表格包含有意义数据: {has_meaningful_data}")
                                    
                                    if has_meaningful_data:
                                        table_element = candidate_table
                                        product_section = elem
                                        print(f"🐛 [DEBUG] ✅ 选中这个表格作为候选")
                                        break
                                        
                            except Exception as e:
                                print(f"🐛 [DEBUG]       分析元素附近表格时出错: {e}")
                                
                except Exception as e:
                    print(f"🐛 [DEBUG]   选择器 {selector_idx+1} 出错: {e}")
                    
                if table_element:
                    break
            
            if table_element:
                break
        
        # 如果没有找到，使用原方法查找最大的表格
        if not table_element:
            print("🐛 [DEBUG] 未通过标题找到表格，分析所有表格选择最佳候选...")
            tables = driver.find_elements(By.TAG_NAME, 'table')
            
            if not tables:
                print("❌ 未找到任何表格")
                return specifications
            
            print(f"🐛 [DEBUG] 页面共有 {len(tables)} 个表格，分析每个表格的质量...")
            
            best_table = None
            best_score = 0
            
            for i, table in enumerate(tables):
                if not table.is_displayed():
                    print(f"🐛 [DEBUG] 表格 {i+1}: 不可见，跳过")
                    continue
                
                rows = table.find_elements(By.TAG_NAME, 'tr')
                score = 0
                non_empty_rows = 0
                
                print(f"🐛 [DEBUG] 表格 {i+1}: {len(rows)} 行")
                
                for j, row in enumerate(rows[:10]):  # 只检查前10行
                    cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                    cell_texts = [cell.text.strip() for cell in cells]
                    non_empty_cells = [text for text in cell_texts if text and len(text) > 1]
                    
                    if j < 3:  # 显示前3行内容
                        cell_texts_short = [text[:20] + "..." if len(text) > 20 else text for text in cell_texts]
                        print(f"🐛 [DEBUG]   行 {j+1}: {cell_texts_short}")
                    
                    if len(non_empty_cells) >= 2:
                        non_empty_rows += 1
                        score += len(non_empty_cells)
                        
                        # 检查是否包含产品编号相关词汇
                        for text in cell_texts:
                            text_lower = text.lower()
                            if any(keyword in text_lower for keyword in ['part', 'number', 'model', 'reference', 'item']):
                                score += 10
                            # 检查是否看起来像产品编号
                            if is_likely_product_reference(text):
                                score += 5
                
                print(f"🐛 [DEBUG] 表格 {i+1} 评分: {score} (非空行: {non_empty_rows})")
                
                if score > best_score:
                    best_score = score
                    best_table = table
                    print(f"🐛 [DEBUG] ✅ 表格 {i+1} 成为最佳候选 (评分: {score})")
            
            table_element = best_table
            if table_element:
                print(f"🐛 [DEBUG] 最终选择表格，评分: {best_score}")
            else:
                print("🐛 [DEBUG] ❌ 没有找到合适的表格")
        
        if not table_element:
            print("❌ 未找到合适的产品表格")
            return specifications
        
        # 分析找到的表格
        rows = table_element.find_elements(By.TAG_NAME, 'tr')
        if not FAST_MODE:
            print(f"📊 分析表格，共 {len(rows)} 行")
        
        # 🐛 DEBUG: 详细分析选中的表格
        print("🐛 [DEBUG] === 选中表格详细分析 ===")
        for i, row in enumerate(rows):
            cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
            cell_texts = [cell.text.strip() for cell in cells]
            cell_tags = [cell.tag_name for cell in cells]
            
            print(f"🐛 [DEBUG] 行 {i+1}: {len(cells)} 个单元格")
            print(f"🐛 [DEBUG]   标签: {cell_tags}")
            print(f"🐛 [DEBUG]   内容: {cell_texts}")
            
            # 检查单元格的属性
            for j, cell in enumerate(cells):
                cell_class = cell.get_attribute('class')
                cell_id = cell.get_attribute('id')
                if cell_class or cell_id:
                    print(f"🐛 [DEBUG]     单元格 {j+1} - class: {cell_class}, id: {cell_id}")
        
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
                
                # 🐛 DEBUG: 详细分析每个值
                print(f"🐛 [DEBUG]     值长度: {len(prop_value)}, 是否可能是产品编号: {is_likely_product_reference(prop_value)}")
                
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
            
            print("🐛 [DEBUG] === 查找表头行 ===")
            for i, row in enumerate(rows):
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                if not cells:
                    continue
                
                cell_texts = [cell.text.strip() for cell in cells]
                
                # 如果是th元素，很可能是表头
                th_cells = row.find_elements(By.TAG_NAME, 'th')
                is_header_row = len(th_cells) == len(cells) and len(th_cells) > 0
                
                print(f"🐛 [DEBUG] 行 {i+1}: {len(cells)} 个单元格, {len(th_cells)} 个th, 是表头: {is_header_row}")
                print(f"🐛 [DEBUG]   内容: {cell_texts}")
                
                if is_header_row:
                    header_row_index = i
                    header_cells = cell_texts
                    print(f"  📋 识别表头行 {i+1}: {header_cells[:5]}...")
                    break
            
            # 确定产品编号列（根据列名）
            product_columns = []
            if header_cells:
                print("🐛 [DEBUG] === 分析表头查找产品编号列 ===")
                for j, header in enumerate(header_cells):
                    header_lower = header.lower()
                    print(f"🐛 [DEBUG] 列 {j+1}: '{header}' (小写: '{header_lower}')")
                    
                    # 匹配各种语言的产品编号列名
                    matching_keywords = []
                    for keyword in [
                        'part number', 'part no', 'part#', 'p/n',
                        'product number', 'product code', 'product id',
                        'model', 'model number', 'model no',
                        'reference', 'ref', 'item number', 'item no',
                        'catalog number', 'cat no', 'sku',
                        'description',  # 🔧 NEW: 添加description作为可能的产品编号列
                        'bestellnummer', 'artikelnummer', 'teilenummer',  # 德语
                        'numéro', 'référence',  # 法语
                        'número', 'codigo',  # 西班牙语
                        '型号', '编号', '料号'  # 中文
                    ]:
                        if keyword in header_lower:
                            matching_keywords.append(keyword)
                    
                    if matching_keywords:
                        product_columns.append(j)
                        print(f"    ✓ 识别产品编号列 {j+1}: '{header}' (匹配: {matching_keywords})")
                        
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
            print("🐛 [DEBUG] === 提取数据行 ===")
            for i, row in enumerate(rows):
                if i <= header_row_index:  # 跳过表头及之前的行
                    print(f"🐛 [DEBUG] 跳过行 {i+1} (表头或之前)")
                    continue
                    
                cells = row.find_elements(By.CSS_SELECTOR, 'td, th')
                if not cells:
                    print(f"🐛 [DEBUG] 行 {i+1}: 无单元格")
                    continue
                
                cell_texts = [cell.text.strip() for cell in cells]
                print(f"🐛 [DEBUG] 数据行 {i+1}: {cell_texts}")
                
                # 查找可能的产品编号
                if use_smart_detection:
                    print(f"🐛 [DEBUG]   使用智能检测模式")
                    # 智能检测模式：扫描所有单元格
                    found_in_row = False
                    for j, cell_text in enumerate(cell_texts):
                        is_likely = is_likely_product_reference(cell_text)
                        print(f"🐛 [DEBUG]     单元格 {j+1}: '{cell_text}' -> 可能是产品编号: {is_likely}")
                        
                        if cell_text and len(cell_text) >= 3 and cell_text not in seen_references:
                            if is_likely:
                                # 🔧 NEW: 特别检查Description列的内容
                                column_name = header_cells[j] if header_cells and j < len(header_cells) else f"列{j+1}"
                                print(f"🔧 [NEW] ✅ 在 {column_name} 中发现产品编号: '{cell_text}'")
                                
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
                                
                                if not FAST_MODE and len(specifications) <= 10:
                                    print(f"  📦 提取规格 {len(specifications)}: {cell_text}")
                                
                                found_in_row = True
                                # 在智能模式下，每行只取第一个符合条件的
                                break
                    
                    if not found_in_row:
                        print(f"🔧 [NEW] ⚠️ 该行未找到有效产品编号: {cell_texts}")
                else:
                    print(f"🐛 [DEBUG]   使用列定位模式，产品编号列: {product_columns}")
                    # 使用识别的产品编号列
                    for col_idx in product_columns:
                        if col_idx < len(cell_texts):
                            cell_text = cell_texts[col_idx]
                            print(f"🐛 [DEBUG]     产品编号列 {col_idx+1}: '{cell_text}'")
                            
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
                                    
                                    if not FAST_MODE and len(specifications) <= 10:
                                        print(f"  📦 提取规格 {len(specifications)}: {cell_text}")
        
        if not FAST_MODE and len(specifications) > 10:
            print(f"  ... 还有 {len(specifications) - 10} 个规格")
            
    except Exception as e:
        print(f"❌ 提取规格时出错: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"✅ 总共提取到 {len(specifications)} 个产品规格")
    
    # 🐛 DEBUG: 最终结果分析
    if DEBUG_MODE:
        print("🐛 [DEBUG] === 最终提取结果分析 ===")
        if specifications:
            for i, spec in enumerate(specifications[:5]):  # 显示前5个
                print(f"🐛 [DEBUG] 规格 {i+1}: {spec}")
        else:
            print("🐛 [DEBUG] ❌ 没有提取到任何规格")
            print("🐛 [DEBUG] 可能的原因:")
            print("🐛 [DEBUG] 1. 页面结构与预期不符")
            print("🐛 [DEBUG] 2. 产品数据通过JavaScript动态加载")
            print("🐛 [DEBUG] 3. 表格中的数据被特殊格式化或隐藏")
            print("🐛 [DEBUG] 4. 产品编号识别规则过于严格")
    
    # 🐛 DEBUG: 保存分析完成后的页面截图
    if DEBUG_MODE and not FAST_MODE:
        try:
            final_screenshot = RESULTS_DIR / f"analysis_complete_{timestamp}.png"
            driver.save_screenshot(str(final_screenshot))
            print(f"🐛 [DEBUG] 分析完成后的页面截图: {final_screenshot}")
        except Exception as e:
            print(f"🐛 [DEBUG] 保存最终截图失败: {e}")
    
    return specifications

def is_likely_product_reference(text):
    """智能判断文本是否可能是产品编号"""
    debug_enabled = os.getenv("DEBUG_PRODUCT_REFERENCE", "false").lower() == "true"
    
    if debug_enabled:
        print(f"🐛 [DEBUG] 分析文本: '{text}'")
    
    if not text or len(text) < 3:
        if debug_enabled:
            print(f"🐛 [DEBUG]   ❌ 文本为空或长度不足3: {len(text) if text else 0}")
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
            if debug_enabled:
                print(f"🐛 [DEBUG]   ❌ 匹配排除模式: {pattern}")
            return False
    
    # 排除纯描述性文本（全是常见英文单词）
    common_words = [
        'description', 'manufacturer', 'material', 'color', 'size',
        'weight', 'length', 'width', 'height', 'diameter', 'thickness'
    ]
    
    text_lower = text.lower()
    if any(text_lower == word for word in common_words):
        if debug_enabled:
            print(f"🐛 [DEBUG]   ❌ 是常见描述词: {text_lower}")
        return False
    
    # 积极的指标：包含这些特征的更可能是产品编号
    positive_indicators = 0
    indicators_found = []
    
    # 1. 包含数字
    if any(c.isdigit() for c in text):
        positive_indicators += 2
        indicators_found.append("包含数字(+2)")
    
    # 2. 包含连字符或下划线
    if '-' in text or '_' in text:
        positive_indicators += 1
        indicators_found.append("包含连字符/下划线(+1)")
    
    # 3. 包含大写字母（不是句子开头）
    if any(c.isupper() for c in text[1:]):
        positive_indicators += 1
        indicators_found.append("包含大写字母(+1)")
    
    # 4. 长度适中（3-50个字符）
    if 3 <= len(text) <= 50:
        positive_indicators += 1
        indicators_found.append("长度适中(+1)")
    
    # 5. 特殊格式模式
    special_patterns = [
        r'^\d+-\d+-\d+$',  # 5-14230-00
        r'^[A-Z]+\d+',     # SLS50, DIN787
        r'^\d+[A-Z]+',     # 14W, 230V
        r'^[A-Z0-9]+[-_][A-Z0-9]+',  # QAAMC10A050S
        r'^[A-Z]{2,}\d{2,}',  # DIN787, EN561
        r'^USC\d+T\d+$',   # 🔧 NEW: USC201T20, USC202T20等NTN产品编号
    ]
    
    for pattern in special_patterns:
        if re.match(pattern, text):
            positive_indicators += 2
            indicators_found.append(f"特殊格式模式(+2): {pattern}")
            break
    
    result = positive_indicators >= 3
    
    if debug_enabled:
        print(f"🐛 [DEBUG]   指标总分: {positive_indicators}")
        print(f"🐛 [DEBUG]   找到指标: {indicators_found}")
        print(f"🐛 [DEBUG]   最终判断: {'✅ 是产品编号' if result else '❌ 不是产品编号'}")
    
    return result

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
    if not FAST_MODE:
        print("\n" + "="*80)
        print("📋 提取结果摘要")
        print("="*80)
        print(f"基础产品URL: {PRODUCT_URL}")
        print(f"找到规格数量: {len(specifications)}")
        print(f"生成链接数量: {len(spec_urls)}")
    else:
        print(f"\n📋 完成: {len(specifications)} 个规格, {len(spec_urls)} 个链接")
    
    if series_stats and not FAST_MODE:
        print(f"\n📊 产品系列分布:")
        for series, count in sorted(series_stats.items()):
            print(f"  {series}: {count} 个规格")
    
    if not FAST_MODE:
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
    if not FAST_MODE:
        print("="*80)

def main():
    start_time = time.time()
    if not FAST_MODE:
        print("🎯 产品规格链接提取器 (重新设计版)")
        print(f"📍 目标产品: {PRODUCT_URL}")
        print("🔄 策略: 一次性加载所有数据，无翻页")
    else:
        print(f"🎯 快速模式提取: {PRODUCT_URL.split('/')[-1][:50]}...")
    
    # 🐛 DEBUG: 启用详细的产品编号识别debug
    if DEBUG_MODE and not FAST_MODE:
        os.environ["DEBUG_PRODUCT_REFERENCE"] = "true"
        print("🐛 [DEBUG] 已启用产品编号识别详细debug模式")
    
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium 未安装，无法运行！")
        return False
    
    # 提取基础产品信息
    base_info = extract_base_product_info(PRODUCT_URL)
    if not base_info:
        print("❌ 无法解析基础产品信息")
        return False
    
    if not FAST_MODE:
        print(f"📦 产品ID: {base_info['product_id']}")
    
    driver = prepare_driver()
    
    try:
        # 访问产品页面
        if not FAST_MODE:
            print(f"🌐 访问产品页面...")
        driver.get(PRODUCT_URL)
        time.sleep(3)
        
        # 处理免责声明弹窗
        close_disclaimer_popup(driver)
        
        # 截图保存初始状态
        if not FAST_MODE:
            screenshot_path = RESULTS_DIR / f"initial_page_{int(time.time())}.png"
            driver.save_screenshot(str(screenshot_path))
            print(f"📸 初始页面截图: {screenshot_path}")
        
        # 尝试设置每页显示为全部
        items_per_page_success = set_items_per_page_to_all(driver)
        
        if items_per_page_success:
            if not FAST_MODE:
                print("✅ 成功设置显示全部项目")
            # 再次截图确认
            if not FAST_MODE:
                final_screenshot = RESULTS_DIR / f"after_show_all_{int(time.time())}.png"
                driver.save_screenshot(str(final_screenshot))
                print(f"📸 设置后截图: {final_screenshot}")
        else:
            if not FAST_MODE:
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
        
        if FAST_MODE:
            print(f"✅ 完成！耗时: {int(time.time() - start_time)} 秒")
        else:
            print("✅ 规格链接提取完成！")
        return True
        
    except Exception as e:
        print(f"❌ 提取过程中发生错误: {e}")
        return False
    finally:
        driver.quit()

def close_disclaimer_popup(driver, timeout=8):
    """关闭可能出现的免责声明弹窗（支持iframe内按钮）"""
    if DEBUG_MODE:
        print("🔧 [POPUP] 尝试检测并关闭免责声明弹窗…")
    
    # 检查域名是否已处理
    current_domain = driver.current_url.split('/')[2]
    if current_domain in _POPUP_HANDLED_DOMAINS:
        return False
    
    accept_keywords = [
        'i understand and accept', 'i understand', 'accept', 'agree',
        'continue', 'ok', 'yes', 'proceed',
        '我理解并接受', '我理解', '接受', '同意', '确认', '继续'
    ]
    
    # FAST_MODE时减少等待时间
    actual_timeout = 3 if FAST_MODE else timeout
    
    try:
        WebDriverWait(driver, actual_timeout).until(
            lambda d: any(
                elem.is_displayed() and elem.size['width'] > 200 and elem.size['height'] > 100
                for elem in d.find_elements(By.XPATH, "//iframe | //div[contains(@class,'modal') or contains(@class,'popup') or contains(@class,'dialog')]")
            )
        )
    except TimeoutException:
        if DEBUG_MODE:
            print("🔧 [POPUP] 未检测到弹窗")
        _POPUP_HANDLED_DOMAINS.add(current_domain)
        return False
    
    # 在默认内容中查找按钮
    for kw in accept_keywords:
        try:
            btn = driver.find_element(By.XPATH, f"//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')]")
            if btn.is_displayed() and btn.is_enabled():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                btn.click()
                if DEBUG_MODE:
                    print(f"🔧 [POPUP] ✅ 点击弹窗按钮: {btn.text.strip()}")
                # 等待弹窗消失
                try:
                    WebDriverWait(driver, 3).until_not(EC.presence_of_element_located((By.XPATH, f"//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')]")))
                except:
                    time.sleep(1 if FAST_MODE else 2)
                _POPUP_HANDLED_DOMAINS.add(current_domain)
                return True
        except Exception:
            continue
    # 如果未找到，检查iframe
    iframes = driver.find_elements(By.TAG_NAME, 'iframe')
    for iframe in iframes:
        if not iframe.is_displayed():
            continue
        try:
            driver.switch_to.frame(iframe)
            for kw in accept_keywords:
                try:
                    btn = driver.find_element(By.XPATH, f"//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')] | //a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{kw}')]")
                    if btn.is_displayed() and btn.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                        btn.click()
                        if DEBUG_MODE:
                            print(f"🔧 [POPUP] ✅ 在iframe中点击按钮: {btn.text.strip()}")
                        driver.switch_to.default_content()
                        # 等待弹窗消失
                        try:
                            WebDriverWait(driver, 3).until_not(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                        except:
                            time.sleep(1 if FAST_MODE else 2)
                        _POPUP_HANDLED_DOMAINS.add(current_domain)
                        return True
                except Exception:
                    continue
            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()
            continue
    print("🔧 [POPUP] ❌ 未能关闭弹窗")
    return False

if __name__ == '__main__':
    success = main()
    print("✅ test-09-1 成功" if success else "❌ test-09-1 失败") 