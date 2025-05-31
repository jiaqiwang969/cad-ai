#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
类目深度爬取测试 - TraceParts 子类目信息抓取
测试进入具体类目页面，提取子类目和链接
"""

import os
import json
import re
import time
import asyncio
import aiofiles
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import random

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate

# 导入selenium相关模块
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

import requests
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
LOG = logging.getLogger("category-drill-down")

# 并发控制常量
MAX_SUBCATEGORY_CONCURRENCY = 2  # 子类目页面的并发数量
MAX_RETRIES = 3
SUBCATEGORY_TIMEOUT = 60
BACKOFF_BASE = 2.0
BACKOFF_JITTER = 0.25

@dataclass
class CategoryDrillConfig:
    """类目深度爬取配置"""
    api_key: str = "sk-YgL2cnnuifh9AloZFa6d63111aC64e4898Ba0769077521Ac"
    base_url: str = "https://ai.pumpkinai.online"
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: int = 3000
    subcategory_concurrency: int = MAX_SUBCATEGORY_CONCURRENCY
    max_retries: int = MAX_RETRIES
    subcategory_timeout: int = SUBCATEGORY_TIMEOUT

@dataclass
class CategoryInfo:
    """类目信息数据结构"""
    name: str
    description: str
    url: str
    parent_category: str = ""
    level: int = 1  # 1=主类目, 2=子类目, 3=子子类目

class CategoryDrillDownExtractor:
    """类目深度爬取器"""
    
    def __init__(self, config: CategoryDrillConfig):
        self.config = config
        self.subcategory_sem = asyncio.Semaphore(config.subcategory_concurrency)
        
        # 配置LLM
        self.llm = ChatOpenAI(
            model=config.model,
            openai_api_key=config.api_key,
            openai_api_base=config.base_url + "/v1",
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
        
        # 子类目提取的AI提示模板
        self.subcategory_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是TraceParts网站的专业分析师。请从产品类目页面中提取完整的多层级子类目信息。

你正在分析一个具体的产品类目页面（如MECHANICAL COMPONENTS），需要提取其下的所有层级子类目。

**重要任务：**
1. 识别页面中的所有子类目名称（二级、三级、四级等）
2. 提取每个子类目对应的完整链接
3. 分析子类目的层级关系
4. 识别子类目的描述信息（如果有）

**特别注意多层级内容格式：**
- 可能包含格式如：🔗 L2 类目: XXX, 🔗 L3 类目: XXX, 🔗 L4 类目: XXX
- 可能包含路径信息：🗂️ 路径: fasteners > washers
- 层级缩进显示：二级类目无缩进，三级类目两个空格缩进

**提取规则：**
- 子类目通常以链接形式出现
- 子类目名称可能是英文或中文
- 优先提取包含以下模式的链接：
  - /search/traceparts-classification-
  - CatalogPath=TRACEPARTS%3A
  - 产品相关的分类链接

**返回格式：**
请返回严格的JSON格式，包含完整的层级信息：

{{
    "subcategories": [
        {{
            "name": "Fasteners",
            "description": "紧固件相关产品",
            "url": "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-fasteners?CatalogPath=TRACEPARTS%3ATP01001",
            "level": 2,
            "parent_path": "MECHANICAL COMPONENTS"
        }},
        {{
            "name": "Screws and bolts",
            "description": "螺丝和螺栓",
            "url": "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-fasteners-screws?CatalogPath=TRACEPARTS%3ATP01001001",
            "level": 3,
            "parent_path": "MECHANICAL COMPONENTS > Fasteners"
        }},
        {{
            "name": "Spherical seat washers",
            "description": "球面垫圈",
            "url": "https://www.traceparts.cn/en/search/traceparts-classification-mechanical-components-fasteners-washers-spherical?CatalogPath=TRACEPARTS%3ATP01001003001",
            "level": 4,
            "parent_path": "MECHANICAL COMPONENTS > Fasteners > Washers"
        }}
    ],
    "parent_info": {{
        "name": "父类目名称",
        "total_subcategories": "子类目总数",
        "level_distribution": {{
            "level_2": "二级类目数量",
            "level_3": "三级类目数量", 
            "level_4": "四级类目数量"
        }}
    }}
}}

**严格要求：**
- 只提取真实存在的链接，不要编造任何URL
- URL必须完整，以https://开头
- level字段必须是数字(2, 3, 4等)
- parent_path要体现完整的层级路径
- 如果没有找到子类目，subcategories数组为空
- 子类目名称要准确，不要翻译或修改
- 优先从内容中标记为"L2 类目"、"L3 类目"等格式的信息中提取"""),
            ("human", "请分析以下TraceParts产品类目页面，提取所有多层级子类目信息。特别注意层级标记(L2、L3、L4)和路径信息。页面内容：\n\n{content}")
        ])

    def load_category_page_selenium(self, category_url: str, category_name: str) -> str:
        """使用Selenium加载具体类目页面并深度挖掘树状结构"""
        LOG.info(f"🌐 加载 {category_name} 类目页面: {category_url}")
        
        if not SELENIUM_AVAILABLE:
            raise Exception("Selenium未安装，请运行：pip install selenium")
        
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            driver.get(category_url)
            
            LOG.info("⏳ 等待类目页面加载...")
            time.sleep(10)  # 增加初始等待时间
            
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                LOG.warning("⚠️  页面加载超时，继续尝试获取内容...")
            
            # 深度挖掘策略开始
            LOG.info("🔍 开始深度挖掘树状导航结构...")
            
            # 1. 尝试展开所有可能的树节点
            self.expand_all_tree_nodes(driver)
            
            # 2. 滚动页面确保动态内容加载
            self.scroll_to_load_dynamic_content(driver)
            
            # 3. 再次等待动态内容加载
            time.sleep(5)
            
            content = driver.page_source
            
            # 4. 深度提取多层级类目结构
            all_subcategories = self.deep_extract_tree_structure(driver, category_name)
            
            if all_subcategories:
                # 构建详细的多层级子类目信息
                detailed_subcategory_info = f"\n\n=== {category_name} 完整树状结构 ===\n"
                detailed_subcategory_info += f"父类目: {category_name}\n"
                detailed_subcategory_info += f"总子类目数量: {len(all_subcategories)}\n\n"
                
                # 按层级组织信息
                level_2_categories = [sub for sub in all_subcategories if sub.get('level', 2) == 2]
                level_3_categories = [sub for sub in all_subcategories if sub.get('level', 2) == 3]
                level_4_categories = [sub for sub in all_subcategories if sub.get('level', 2) == 4]
                
                detailed_subcategory_info += f"二级类目: {len(level_2_categories)} 个\n"
                detailed_subcategory_info += f"三级类目: {len(level_3_categories)} 个\n"
                detailed_subcategory_info += f"四级类目: {len(level_4_categories)} 个\n\n"
                
                for item in all_subcategories:
                    level_prefix = "  " * (item.get('level', 2) - 2)
                    detailed_subcategory_info += f"{level_prefix}🔗 L{item.get('level', 2)} 类目: {item['name']}\n"
                    detailed_subcategory_info += f"{level_prefix}🌐 链接: {item['url']}\n"
                    detailed_subcategory_info += f"{level_prefix}📂 父类目: {item['parent_category']}\n"
                    if 'parent_path' in item:
                        detailed_subcategory_info += f"{level_prefix}🗂️  路径: {item['parent_path']}\n"
                    detailed_subcategory_info += f"{level_prefix}" + "=" * 50 + "\n"
                
                content += detailed_subcategory_info
                LOG.info(f"✅ 深度挖掘成功提取了 {len(all_subcategories)} 个多层级子类目")
                
                # 显示层级统计
                LOG.info("📊 层级分布统计:")
                LOG.info(f"  二级类目: {len(level_2_categories)} 个")
                LOG.info(f"  三级类目: {len(level_3_categories)} 个") 
                LOG.info(f"  四级类目: {len(level_4_categories)} 个")
                
            else:
                LOG.warning(f"⚠️  深度挖掘未找到 {category_name} 的子类目")
            
            driver.quit()
            
            LOG.info(f"✅ {category_name} 页面深度分析完成，内容长度: {len(content)} 字符")
            return content
            
        except Exception as e:
            LOG.error(f"❌ {category_name} 页面加载失败: {str(e)}")
            raise

    def expand_all_tree_nodes(self, driver):
        """展开所有可能的树节点"""
        LOG.info("🌳 尝试展开所有树状导航节点...")
        
        # 可能的展开按钮选择器
        expand_selectors = [
            "button[aria-expanded='false']",     # ARIA展开按钮
            ".tree-toggle",                      # 树状切换按钮
            ".expand-button",                    # 展开按钮
            ".collapse-toggle",                  # 折叠切换
            "[role='button'][aria-expanded='false']",  # ARIA按钮
            ".fa-plus",                         # Font Awesome plus图标
            ".fa-chevron-right",                # Font Awesome右箭头
            "span.toggle",                      # 切换span
            ".jstree-closed > .jstree-icon",    # jsTree关闭节点
            ".fancytree-closed .fancytree-expander",  # fancyTree关闭节点
        ]
        
        expanded_count = 0
        for selector in expand_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                LOG.info(f"  找到 {len(elements)} 个 '{selector}' 展开元素")
                
                for element in elements[:50]:  # 限制数量避免无限循环
                    try:
                        if element.is_displayed() and element.is_enabled():
                            driver.execute_script("arguments[0].click();", element)
                            expanded_count += 1
                            time.sleep(0.5)  # 等待展开动画
                    except:
                        continue
                        
            except Exception as e:
                LOG.debug(f"  展开选择器 '{selector}' 失败: {str(e)}")
        
        LOG.info(f"✅ 总共展开了 {expanded_count} 个树节点")

    def scroll_to_load_dynamic_content(self, driver):
        """滚动页面以加载动态内容"""
        LOG.info("📜 滚动页面加载动态内容...")
        
        try:
            # 获取页面总高度
            total_height = driver.execute_script("return document.body.scrollHeight")
            current_position = 0
            
            # 分段滚动
            while current_position < total_height:
                # 向下滚动
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(1)
                current_position += 500
                
                # 检查是否有新内容加载
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height > total_height:
                    total_height = new_height
                    LOG.info(f"📈 检测到新内容，页面高度增加到 {total_height}px")
            
            # 滚动到顶部
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            LOG.info("✅ 页面滚动完成")
            
        except Exception as e:
            LOG.warning(f"⚠️  页面滚动失败: {str(e)}")

    def deep_extract_tree_structure(self, driver, category_name: str) -> List[Dict[str, Any]]:
        """深度提取完整的树状结构"""
        LOG.info("🎯 深度提取完整树状结构...")
        
        all_subcategories = []
        
        # 高精度选择器策略
        high_precision_selectors = [
            # 直接匹配所有TraceParts分类链接
            "a[href*='traceparts-classification-']",              # 所有分类链接
            "a[href*='CatalogPath=TRACEPARTS%3A']",               # 所有目录路径链接
            # 树状结构选择器
            "li a[href*='classification']",                       # 列表中的分类链接
            "ul li a[href*='traceparts']",                        # 无序列表中的TraceParts链接
            # 侧边栏导航
            ".sidebar a[href*='classification']",                 # 侧边栏分类链接
            "nav a[href*='classification']",                      # 导航区分类链接
            "aside a[href*='classification']",                    # aside区域分类链接
            # 特定的导航结构
            "[role='tree'] a",                                    # ARIA树结构
            "[role='treeitem'] a",                                # ARIA树项
            ".tree a",                                            # 树状组件
            ".nav-tree a",                                        # 导航树
            # 通用但有效的选择器
            "a[href*='search/traceparts-classification']",        # 搜索分类链接
            "a[title*='classification']",                         # 标题包含classification
            ".classification a",                                  # 分类class下的链接
        ]
        
        seen_urls = set()
        seen_texts = set()
        
        for selector in high_precision_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                LOG.info(f"  高精度选择器 '{selector}' 找到 {len(elements)} 个元素")
                
                for element in elements:
                    try:
                        text = element.text.strip()
                        href = element.get_attribute('href') or ""
                        
                        if not text or len(text) < 2 or len(text) > 200:
                            continue
                        
                        # 更精确的机械组件子类目判断
                        if not self.is_valid_mechanical_subcategory(text, href):
                            continue
                        
                        # 构建完整URL
                        if href and not href.startswith('http'):
                            if href.startswith('/'):
                                href = f"https://www.traceparts.cn{href}"
                        
                        # 去重
                        if href in seen_urls or text.upper() in seen_texts:
                            continue
                        
                        seen_urls.add(href)
                        seen_texts.add(text.upper())
                        
                        # 分析层级
                        level, parent_path = self.analyze_category_level(text, href, element)
                        
                        subcategory = {
                            "name": text,
                            "url": href,
                            "level": level,
                            "parent_category": category_name,
                            "parent_path": parent_path,
                            "element_tag": element.tag_name,
                            "extraction_method": "deep_tree_analysis"
                        }
                        
                        all_subcategories.append(subcategory)
                        LOG.debug(f"    深度提取: L{level} '{text}' -> {href[:80]}...")
                        
                    except Exception as e:
                        continue
                        
            except Exception as e:
                LOG.debug(f"  高精度选择器 '{selector}' 失败: {str(e)}")
        
        # 按层级和名称排序
        all_subcategories.sort(key=lambda x: (x['level'], x['name']))
        
        LOG.info(f"🎯 深度提取完成，共获得 {len(all_subcategories)} 个多层级子类目")
        return all_subcategories

    def is_valid_mechanical_subcategory(self, text: str, href: str) -> bool:
        """判断是否为有效的TraceParts分类子类目（扩展到所有类目）"""
        text_lower = text.lower()
        href_lower = href.lower()
        
        # 排除模式
        exclude_patterns = [
            'sign-in', 'sign-up', 'login', 'register', 'news', 'blog',
            'help', 'support', 'contact', 'about', 'home', 'search?q=',
            'cookie', 'privacy', 'terms', 'javascript:', 'mailto:'
        ]
        
        if any(pattern in text_lower or pattern in href_lower for pattern in exclude_patterns):
            return False
        
        # 扩展的TraceParts所有类目关键词
        all_category_keywords = [
            # 机械组件
            'mechanical', 'fastener', 'screw', 'bolt', 'nut', 'washer', 'rivet', 'pin',
            'anchor', 'stud', 'thread', 'insert', 'lock', 'retaining', 'bearing', 'seal',
            'gasket', 'o-ring', 'ring', 'spring', 'damper', 'shock', 'vibration',
            'gear', 'pulley', 'belt', 'chain', 'coupling', 'joint', 'transmission',
            'drive', 'clutch', 'brake', 'linear', 'slide', 'guide', 'rail', 'actuator',
            'cylinder', 'piston', 'rod', 'shaft', 'spindle',
            
            # 电气组件
            'electrical', 'electronic', 'connector', 'cable', 'wire', 'switch',
            'relay', 'sensor', 'circuit', 'breaker', 'fuse', 'terminal', 'plug',
            'socket', 'junction', 'panel', 'meter', 'transformer', 'capacitor',
            'resistor', 'inductor', 'diode', 'transistor',
            
            # 材料
            'material', 'steel', 'stainless', 'aluminum', 'brass', 'copper', 'plastic',
            'rubber', 'ceramic', 'composite', 'bar', 'beam', 'tube', 'pipe', 'sheet',
            'plate', 'profile', 'angle', 'channel', 'round', 'square', 'flat',
            
            # 液压气动
            'hydraulic', 'pneumatic', 'valve', 'pump', 'filter', 'regulator',
            'accumulator', 'reservoir', 'manifold', 'fitting', 'hose', 'cylinder',
            'motor', 'compressor', 'air', 'oil', 'fluid',
            
            # 光学
            'optic', 'optical', 'lens', 'mirror', 'prism', 'fiber', 'laser',
            'camera', 'detector', 'filter', 'window', 'dome',
            
            # 真空设备
            'vacuum', 'pump', 'chamber', 'valve', 'gauge', 'fitting',
            
            # 热传导
            'heat', 'thermal', 'cooler', 'heater', 'exchanger', 'radiator',
            'insulation', 'thermostat', 'temperature',
            
            # 建筑施工
            'building', 'construction', 'concrete', 'brick', 'mortar', 'cement',
            'aggregate', 'reinforcement', 'formwork', 'scaffold',
            
            # 土木工程
            'civil', 'engineering', 'infrastructure', 'road', 'bridge', 'tunnel',
            'foundation', 'drainage', 'pavement',
            
            # 标准和规格
            'din', 'iso', 'ansi', 'astm', 'jis', 'gb', 'metric', 'imperial',
            'standard', 'specification', 'grade', 'class'
        ]
        
        # URL包含分类特征（最重要）
        if 'traceparts-classification-' in href_lower or 'catalogpath=traceparts' in href_lower:
            return True
        
        # 文本包含任何类目关键词
        if any(keyword in text_lower for keyword in all_category_keywords):
            return True
        
        # 格式像类目名称
        if (len(text.split()) <= 6 and 
            len(text) >= 3 and 
            text[0].isupper() and
            not any(skip in text_lower for skip in ['view', 'show', 'more', 'see all', 'browse', 'click'])):
            return True
        
        return False

    def analyze_category_level(self, text: str, href: str, element) -> tuple:
        """分析类目层级和路径"""
        try:
            # 通过URL路径分析层级
            if 'traceparts-classification-' in href:
                # 分析完整的分类路径
                classification_part = href.split('traceparts-classification-')[1].split('?')[0]
                
                if classification_part == '':
                    # 根分类
                    level = 1
                    parent_path = "TraceParts Classification"
                else:
                    # 计算层级深度
                    parts = classification_part.split('-')
                    level = min(len(parts) + 1, 6)  # 限制最大层级为6
                    
                    # 构建父路径
                    if level == 2:
                        parent_path = "TraceParts Classification"
                    else:
                        parent_path = "TraceParts Classification > " + ' > '.join(parts[:-1])
            else:
                level = 2
                parent_path = "TraceParts Classification"
            
            # 通过DOM结构分析层级（如果可能）
            try:
                parent_li = element.find_element(By.XPATH, "./..")
                nested_level = 0
                current = parent_li
                
                # 向上查找嵌套的ul/li结构
                for _ in range(5):  # 最多查找5层
                    try:
                        current = current.find_element(By.XPATH, "../..")
                        if current.tag_name.lower() in ['ul', 'ol']:
                            nested_level += 1
                    except:
                        break
                
                if nested_level > 0:
                    level = max(level, nested_level + 1)
                    
            except:
                pass  # DOM分析失败不影响URL分析
            
            return level, parent_path
            
        except:
            return 2, "TraceParts Classification"

    async def extract_subcategories(self, category_info: CategoryInfo) -> Dict[str, Any]:
        """异步提取子类目信息"""
        LOG.info(f"🔍 开始分析 {category_info.name} 的子类目...")
        
        selenium_subcategories = []  # 存储Selenium直接提取的结果
        
        async with self.subcategory_sem:
            try:
                # 在线程池中加载页面内容
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    content = await loop.run_in_executor(
                        executor,
                        self.load_category_page_selenium,
                        category_info.url,
                        category_info.name
                    )
                
                # 从Selenium加载过程中提取子类目数据（直接从日志记录中获取）
                # 检查content中是否包含我们添加的子类目信息
                content_markers = [
                    f"=== {category_info.name} 完整树状结构 ===",  # 新格式
                    f"=== {category_info.name} 子类目信息 ==="      # 旧格式兼容
                ]
                
                found_content_marker = any(marker in content for marker in content_markers)
                
                if found_content_marker:
                    LOG.info("📦 发现Selenium提取的子类目信息，尝试解析...")
                    selenium_subcategories = self.extract_selenium_subcategories_from_content(content, category_info.name)
                    LOG.info(f"📦 从Selenium内容中解析到 {len(selenium_subcategories)} 个子类目")
                
                # 分割内容进行AI分析
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=4000,
                    chunk_overlap=300,
                    separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
                    length_function=len,
                )
                chunks = text_splitter.split_text(content)
                LOG.info(f"📄 {category_info.name} 内容分割为 {len(chunks)} 个块")
                
                # AI分析前几个有效块
                ai_subcategories = []
                for chunk in chunks[:3]:  # 分析前3个块
                    if len(chunk) > 1000:  # 只分析有足够内容的块
                        try:
                            with ThreadPoolExecutor() as executor:
                                chain = self.subcategory_prompt | self.llm
                                
                                future = executor.submit(
                                    chain.invoke,
                                    {"content": chunk}
                                )
                                
                                response = await asyncio.wait_for(
                                    asyncio.wrap_future(future),
                                    timeout=self.config.subcategory_timeout
                                )
                            
                            # 解析AI响应
                            chunk_subcategories = self.parse_subcategory_response(response.content, category_info.name)
                            if chunk_subcategories:
                                ai_subcategories.extend(chunk_subcategories)
                                LOG.info(f"✅ AI分析块 {len(ai_subcategories)} 提取到子类目")
                                break  # 找到一个有效的就退出
                        except Exception as e:
                            LOG.warning(f"⚠️  AI分析块失败: {str(e)}")
                            continue
                
                # 决定使用哪个结果：优先AI结果，fallback到Selenium结果
                final_subcategories = []
                extraction_method = ""
                
                if ai_subcategories:
                    final_subcategories = ai_subcategories
                    extraction_method = "AI_analysis"
                    LOG.info(f"✅ 使用AI分析结果: {len(final_subcategories)} 个子类目")
                elif selenium_subcategories:
                    final_subcategories = selenium_subcategories
                    extraction_method = "selenium_direct"
                    LOG.info(f"✅ 使用Selenium直接提取结果: {len(final_subcategories)} 个子类目")
                else:
                    LOG.warning(f"⚠️  AI和Selenium都未能提取到 {category_info.name} 的子类目")
                
                if final_subcategories:
                    return {
                        "parent_category": category_info.name,
                        "parent_url": category_info.url,
                        "subcategories": final_subcategories,
                        "extraction_method": extraction_method,
                        "extraction_time": datetime.now().isoformat()
                    }
                else:
                    return {
                        "parent_category": category_info.name,
                        "parent_url": category_info.url,
                        "subcategories": [],
                        "extraction_method": "failed",
                        "extraction_time": datetime.now().isoformat()
                    }
                
            except Exception as e:
                LOG.error(f"❌ {category_info.name} 子类目提取失败: {str(e)}")
                # 即使出错，也尝试返回Selenium结果
                if selenium_subcategories:
                    LOG.info(f"🔄 使用Selenium备份结果: {len(selenium_subcategories)} 个子类目")
                    return {
                        "parent_category": category_info.name,
                        "parent_url": category_info.url,
                        "subcategories": selenium_subcategories,
                        "extraction_method": "selenium_backup",
                        "error": str(e),
                        "extraction_time": datetime.now().isoformat()
                    }
                
                return {
                    "parent_category": category_info.name,
                    "parent_url": category_info.url,
                    "subcategories": [],
                    "error": str(e),
                    "extraction_method": "failed",
                    "extraction_time": datetime.now().isoformat()
                }

    def extract_selenium_subcategories_from_content(self, content: str, parent_name: str) -> List[Dict[str, Any]]:
        """从Selenium添加到content中的子类目信息解析出子类目列表"""
        subcategories = []
        
        try:
            # 查找多层级子类目信息段落 - 更新标记
            start_markers = [
                f"=== {parent_name} 完整树状结构 ===",  # 新格式
                f"=== {parent_name} 子类目信息 ==="      # 旧格式兼容
            ]
            
            found_marker = None
            for marker in start_markers:
                if marker in content:
                    found_marker = marker
                    break
            
            if found_marker:
                LOG.info(f"📦 找到标记: {found_marker}")
                start_idx = content.find(found_marker)
                remaining_content = content[start_idx:]
                
                # 更新正则表达式支持多层级格式
                patterns = [
                    # 新的多层级格式：🔗 L2 类目: XXX
                    r'🔗 L(\d+) 类目: (.+?)\n.*?🌐 链接: (.+?)\n.*?📂 父类目: (.+?)\n',
                    # 旧格式兼容：🔗 子类目: XXX  
                    r'🔗 子类目: (.+?)\n🌐 链接: (.+?)\n📂 父类目: (.+?)\n'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, remaining_content, re.DOTALL)
                    LOG.info(f"📦 正则模式匹配到 {len(matches)} 个结果")
                    
                    if matches:
                        for match in matches:
                            if len(match) == 4:  # 新格式：(level, name, url, parent)
                                level, name, url, parent = match
                                level = int(level)
                            else:  # 旧格式：(name, url, parent)
                                name, url, parent = match
                                level = 2
                            
                            if name.strip() and url.strip():
                                subcategory = {
                                    "name": name.strip(),
                                    "description": f"{name.strip()}子类目",
                                    "url": url.strip(),
                                    "level": level,
                                    "parent_category": parent.strip(),
                                    "extraction_method": "selenium_parsed"
                                }
                                subcategories.append(subcategory)
                                LOG.debug(f"📦 解析子类目: L{level} {name.strip()}")
                        
                        break  # 找到匹配就停止
                
                LOG.info(f"📦 从内容中解析出 {len(subcategories)} 个子类目")
                return subcategories
            else:
                LOG.warning("📦 未找到任何标记")
            
        except Exception as e:
            LOG.warning(f"⚠️  解析Selenium内容失败: {str(e)}")
        
        return []

    def parse_subcategory_response(self, response_content: str, parent_name: str) -> List[Dict[str, Any]]:
        """解析AI的子类目响应"""
        subcategories = []
        
        try:
            # 清理响应内容
            cleaned_content = response_content.strip()
            if cleaned_content.startswith('```json'):
                cleaned_content = re.sub(r'^```json\s*', '', cleaned_content)
            if cleaned_content.endswith('```'):
                cleaned_content = re.sub(r'\s*```$', '', cleaned_content)
            
            result = json.loads(cleaned_content)
            
            if "subcategories" in result and isinstance(result["subcategories"], list):
                for sub in result["subcategories"]:
                    if isinstance(sub, dict) and "name" in sub:
                        clean_name = sub["name"].strip()
                        if clean_name:
                            subcategories.append({
                                "name": clean_name,
                                "description": sub.get("description", "").strip(),
                                "url": sub.get("url", ""),
                                "level": sub.get("level", 2),
                                "parent_category": parent_name
                            })
                
                LOG.debug(f"{parent_name} JSON解析成功，提取到 {len(subcategories)} 个子类目")
                return subcategories
                
        except json.JSONDecodeError as e:
            LOG.debug(f"{parent_name} JSON解析失败: {str(e)}")
        
        # 如果JSON解析失败，返回空列表
        return []

async def test_category_drill_down():
    """测试类目深度爬取"""
    LOG.info("=" * 80)
    LOG.info("🔧 TraceParts 完整分类树提取测试 - 根分类页面深度分析")
    LOG.info("=" * 80)
    
    # 目标：TraceParts根分类页面（包含完整树状结构）
    root_classification = CategoryInfo(
        name="TraceParts Classification",
        description="TraceParts完整分类树",
        url="https://www.traceparts.cn/en/search/traceparts-classification?CatalogPath=TRACEPARTS%3ATRACEPARTS",
        level=1
    )
    
    config = CategoryDrillConfig()
    
    try:
        # 初始化提取器
        LOG.info("🔧 初始化完整分类树提取器...")
        extractor = CategoryDrillDownExtractor(config)
        LOG.info("✅ 提取器初始化完成")
        
        # 提取完整分类树
        start_time = time.time()
        result = await extractor.extract_subcategories(root_classification)
        extraction_time = time.time() - start_time
        
        # 构建最终结果
        final_result = {
            "drill_down_result": result,
            "metadata": {
                "target_category": root_classification.name,
                "target_url": root_classification.url,
                "extraction_date": datetime.now().isoformat(),
                "extraction_time_seconds": round(extraction_time, 2),
                "selenium_available": SELENIUM_AVAILABLE,
                "extraction_scope": "complete_classification_tree",
                "config": {
                    "subcategory_concurrency": config.subcategory_concurrency,
                    "max_retries": config.max_retries,
                    "subcategory_timeout": config.subcategory_timeout
                }
            }
        }
        
        # 保存结果
        LOG.info("💾 正在保存完整分类树提取结果...")
        os.makedirs("results", exist_ok=True)
        filepath = "results/traceparts_complete_classification_tree.json"
        
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(final_result, ensure_ascii=False, indent=2))
        
        LOG.info(f"✅ 结果已保存到: {filepath}")
        
        LOG.info("\n" + "=" * 80)
        LOG.info("📋 完整分类树提取结果摘要:")
        LOG.info("=" * 80)
        
        subcategories = result.get("subcategories", [])
        subcategory_count = len(subcategories)
        
        LOG.info(f"🎯 根分类: {root_classification.name}")
        LOG.info(f"🔗 根分类链接: {root_classification.url}")
        LOG.info(f"📊 提取到的总类目数量: {subcategory_count} 个")
        LOG.info(f"⏱️  提取时间: {extraction_time:.2f} 秒")
        LOG.info(f"📁 结果文件: {filepath}")
        
        if subcategory_count > 0:
            # 统计各主类目下的子类目数量
            main_categories = {}
            for sub in subcategories:
                # 分析主类目
                if sub.get('level', 2) == 2:  # 主类目
                    main_category = sub['name']
                    if main_category not in main_categories:
                        main_categories[main_category] = {'count': 0, 'subcats': []}
                    main_categories[main_category]['count'] += 1
                elif sub.get('level', 2) > 2:  # 子类目
                    parent_path = sub.get('parent_path', '')
                    if '>' in parent_path:
                        main_category = parent_path.split('>')[0].strip()
                    else:
                        main_category = "其他"
                    if main_category not in main_categories:
                        main_categories[main_category] = {'count': 0, 'subcats': []}
                    main_categories[main_category]['count'] += 1
                    main_categories[main_category]['subcats'].append(sub['name'])
            
            LOG.info(f"\n🗂️  主类目分布统计:")
            for main_cat, info in main_categories.items():
                LOG.info(f"  📁 {main_cat}: {info['count']} 个子类目")
                if info['subcats']:
                    sample_subcats = info['subcats'][:3]
                    LOG.info(f"      示例: {', '.join(sample_subcats)}{'...' if len(info['subcats']) > 3 else ''}")
            
            LOG.info("\n🔖 提取到的所有类目:")
            for i, sub in enumerate(subcategories[:20]):  # 显示前20个
                name = sub.get('name', 'N/A')
                level = sub.get('level', 2)
                url = sub.get('url', '')
                indent = "  " * (level - 2)
                LOG.info(f"  {i+1}. {indent}L{level} {name}")
                if url and i < 10:  # 只显示前10个的URL
                    LOG.info(f"      {indent}-> {url[:100]}{'...' if len(url) > 100 else ''}")
                    
            if subcategory_count > 20:
                LOG.info(f"  ... 还有 {subcategory_count - 20} 个类目")
        else:
            LOG.warning("\n⚠️  未提取到类目，可能原因:")
            LOG.warning("  1. 页面结构与预期不同")
            LOG.warning("  2. 需要调整选择器策略")
            LOG.warning("  3. 页面需要更多加载时间")
            LOG.warning("  4. 根分类页面可能需要特殊处理")
        
        LOG.info("=" * 80)
        LOG.info("🎉 完整分类树提取测试完成！")
        
        return subcategory_count > 0
        
    except Exception as e:
        LOG.error(f"❌ 测试失败: {str(e)}")
        LOG.info("=" * 80)
        return False

def test_drill_down():
    """同步包装函数"""
    return asyncio.run(test_category_drill_down())

if __name__ == "__main__":
    success = test_drill_down()
    
    if success:
        print("✅ TraceParts 类目深度爬取测试成功完成！")
    else:
        print("❌ TraceParts 类目深度爬取测试失败！")
        print("💡 建议：检查网络连接和Selenium配置")
        
    exit(0 if success else 1)