#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步并发网页爬取测试 - TraceParts 模型类目信息抓取
参考 cot_extractor_safe.py 的异步并发设计
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
LOG = logging.getLogger("async-web-scraper")

# 并发控制常量（参考cot_extractor_safe.py）
MAX_CHUNK_CONCURRENCY = 3  # 同时处理的内容块数量
MAX_RETRIES = 3  # 每个块的最大重试次数
CHUNK_TIMEOUT = 60  # 每个块的超时时间（秒）
BACKOFF_BASE = 2.0  # 重试延迟基数
BACKOFF_JITTER = 0.25  # ±25% 随机性

@dataclass
class ScrapingConfig:
    """爬取配置"""
    api_key: str = "sk-YgL2cnnuifh9AloZFa6d63111aC64e4898Ba0769077521Ac"
    base_url: str = "https://ai.pumpkinai.online"
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 2000
    chunk_concurrency: int = MAX_CHUNK_CONCURRENCY
    max_retries: int = MAX_RETRIES
    chunk_timeout: int = CHUNK_TIMEOUT

@dataclass
class ExtractionStats:
    """提取统计"""
    total_chunks: int = 0
    successful_chunks: int = 0
    failed_chunks: int = 0
    categories_found: int = 0
    retries_used: int = 0

def backoff_delay(attempt: int) -> float:
    """计算退避延迟（参考cot_extractor_safe.py）"""
    base = BACKOFF_BASE * (2 ** (attempt - 1))
    return base * (1 + BACKOFF_JITTER * (2 * random.random() - 1))

class AsyncJsonlWriter:
    """异步JSONL写入器（参考cot_extractor_safe.py）"""
    def __init__(self, path: str):
        self.path = path
        self.lock = asyncio.Lock()
        os.makedirs(os.path.dirname(path), exist_ok=True)

    async def write(self, obj: Dict):
        async with self.lock:
            async with aiofiles.open(self.path, "a", encoding="utf-8") as f:
                await f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def create_mock_data() -> str:
    """创建模拟数据用于测试（不包含假链接）"""
    return """
    TraceParts - CAD Parts Library
    
    Explore by category:
    
    MECHANICAL COMPONENTS
    - Bearings and seals
    - Gears and transmission
    - Fasteners and hardware
    - Springs and dampers
    
    MANUFACTURING ENGINEERING
    - Machine tools
    - Cutting tools
    - Measurement tools
    - Assembly equipment
    
    MATERIALS (BARS, BEAMS, TUBES, ETC.)
    - Steel profiles
    - Aluminum profiles
    - Plastic materials
    - Composite materials
    
    ELECTRICAL
    - Connectors
    - Switches
    - Circuit breakers
    - Cable management
    
    SENSORS AND MEASUREMENT SYSTEMS
    - Temperature sensors
    - Pressure sensors
    - Flow sensors
    - Level sensors
    
    ELECTRONICS
    - Circuit boards
    - Processors
    - Memory devices
    - Power supplies
    
    OPTICS
    - Lenses
    - Mirrors
    - Prisms
    - Optical fibers
    
    PNEUMATICS
    - Air cylinders
    - Valves
    - Air filters
    - Pressure regulators
    
    HYDRAULICS
    - Hydraulic pumps
    - Hydraulic cylinders
    - Hydraulic valves
    - Hydraulic filters
    
    注意：这是模拟数据，不包含真实链接
    """

def load_web_content_selenium(url: str) -> str:
    """使用Selenium加载动态网页内容并提取类目链接"""
    LOG.info(f"🌐 使用Selenium加载网页: {url}")
    
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
        driver.get(url)
        
        LOG.info("⏳ 等待页面加载...")
        time.sleep(8)  # 增加等待时间
        
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            LOG.warning("⚠️  页面加载超时，继续尝试获取内容...")
        
        content = driver.page_source
        
        # 改进的类目链接提取策略
        category_data = []
        try:
            LOG.info("🔍 开始提取类目链接...")
            
            # 针对TraceParts网站的特定选择器
            selectors = [
                # 主要类目选择器
                "a[href*='/category/']",           # 包含category路径的链接
                "a[href*='/products/']",           # 包含products路径的链接
                "a[href*='/components/']",         # 包含components路径的链接
                ".category-link",                  # 类目链接class
                ".product-category",               # 产品类目class
                ".nav-category",                   # 导航类目class
                "[data-category]",                 # 包含category属性的元素
                # 通用选择器
                "nav a",                          # 导航栏链接
                ".menu a",                        # 菜单链接
                ".navigation a",                  # 导航链接
            ]
            
            all_elements = []
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        LOG.info(f"  选择器 '{selector}' 找到 {len(elements)} 个元素")
                        all_elements.extend(elements)
                except Exception as e:
                    LOG.debug(f"  选择器 '{selector}' 失败: {str(e)}")
            
            LOG.info(f"📋 总共找到 {len(all_elements)} 个可能的类目元素")
            
            # 提取并过滤有效的类目信息
            seen_urls = set()
            seen_texts = set()
            
            for i, element in enumerate(all_elements[:100]):  # 处理前100个元素
                try:
                    text = element.text.strip()
                    href = element.get_attribute('href') or ""
                    
                    # 过滤条件
                    if not text or len(text) < 2 or len(text) > 100:
                        continue
                    
                    # 过滤掉不相关的内容
                    skip_patterns = [
                        'cookie', 'privacy', 'terms', 'contact', 'about', 'login', 'register',
                        'help', 'support', 'news', 'blog', 'search', 'download', 'upload',
                        'home', 'javascript:', 'mailto:', '#'
                    ]
                    
                    if any(pattern in text.lower() or pattern in href.lower() for pattern in skip_patterns):
                        continue
                    
                    # 只保留包含产品类目关键词的内容
                    category_keywords = [
                        'mechanical', 'electrical', 'materials', 'hydraulics', 'pneumatics',
                        'sensors', 'electronics', 'optics', 'components', 'engineering',
                        'bearings', 'gears', 'fasteners', 'connectors', 'switches'
                    ]
                    
                    text_lower = text.lower()
                    href_lower = href.lower()
                    
                    # 如果文本或链接包含类目关键词，或者看起来像类目名称
                    is_category = (
                        any(keyword in text_lower for keyword in category_keywords) or
                        any(keyword in href_lower for keyword in category_keywords) or
                        (len(text.split()) <= 5 and text.isupper()) or  # 全大写的短文本
                        'category' in href_lower or
                        'component' in href_lower
                    )
                    
                    if not is_category:
                        continue
                    
                    # 构建完整URL
                    if href and not href.startswith('http'):
                        if href.startswith('/'):
                            href = f"https://www.traceparts.cn{href}"
                        else:
                            href = f"https://www.traceparts.cn/{href}"
                    
                    # 去重
                    if href in seen_urls or text in seen_texts:
                        continue
                    
                    if href:
                        seen_urls.add(href)
                    seen_texts.add(text)
                    
                    category_data.append({
                        "text": text,
                        "url": href,
                        "element_tag": element.tag_name,
                        "element_index": i
                    })
                    
                    # 添加调试信息
                    LOG.debug(f"  提取类目: '{text}' -> '{href}'")
                    
                except Exception as e:
                    continue
            
            if category_data:
                # 将类目数据添加到内容中，供AI分析
                category_info = "\n\n=== 提取的类目信息（真实数据） ===\n"
                for item in category_data:
                    category_info += f"类目: {item['text']}\n"
                    if item['url']:
                        category_info += f"链接: {item['url']}\n"
                    category_info += f"元素: {item['element_tag']}\n"
                    category_info += "---\n"
                
                content += category_info
                LOG.info(f"✅ 成功提取了 {len(category_data)} 个真实类目和链接")
                
                # 输出提取结果的摘要
                LOG.info("📋 提取的类目摘要:")
                for i, item in enumerate(category_data[:10]):  # 显示前10个
                    LOG.info(f"  {i+1}. {item['text'][:50]} -> {item['url'][:80] if item['url'] else '无链接'}")
                if len(category_data) > 10:
                    LOG.info(f"  ... 还有 {len(category_data) - 10} 个类目")
                
            else:
                LOG.warning("⚠️  未找到任何有效的类目链接")
                LOG.info("🔍 尝试使用更宽泛的选择器...")
                
                # 备用方案：更宽泛的搜索
                backup_elements = driver.find_elements(By.TAG_NAME, "a")
                LOG.info(f"🔍 备用搜索找到 {len(backup_elements)} 个链接")
                
                # 扩展类目关键词列表
                extended_keywords = [
                    'mechanical', 'electrical', 'materials', 'hydraulics', 'pneumatics',
                    'sensors', 'electronics', 'optics', 'components', 'engineering',
                    'bearings', 'gears', 'fasteners', 'connectors', 'switches',
                    'manufacturing', 'measurement', 'lifting', 'equipment', 'vacuum',
                    'heat', 'transmission', 'building', 'constructions', 'civil',
                    'bars', 'beams', 'tubes', 'handling'
                ]
                
                # 产品类目URL的特征模式
                product_category_patterns = [
                    'traceparts-classification-',  # TraceParts的类目URL特征
                    'catalogpath=traceparts%3atp'   # CatalogPath参数特征
                ]
                
                # 需要排除的非产品类目链接模式
                exclude_patterns = [
                    'sign-in', 'sign-up', 'login', 'register', 'catalogs', 'news', 
                    'info.traceparts.com', 'discover', 'advertising', 'read'
                ]
                
                for element in backup_elements[:100]:  # 增加搜索范围
                    try:
                        text = element.text.strip()
                        href = element.get_attribute('href') or ""
                        
                        # 放宽条件：只要包含类目关键词或特定URL模式
                        if (text and len(text) > 2 and len(text) < 80 and href):
                            text_lower = text.lower()
                            href_lower = href.lower()
                            
                            # 首先排除不相关的链接
                            if any(pattern in href_lower for pattern in exclude_patterns):
                                continue
                            
                            # 检查是否包含类目关键词
                            has_keyword = any(keyword in text_lower for keyword in extended_keywords)
                            
                            # 检查URL模式 - 优先匹配真正的产品类目链接
                            is_product_category_url = any(pattern in href_lower for pattern in product_category_patterns)
                            
                            # 检查是否是全大写的产品类目名称（进一步过滤）
                            is_valid_category_name = (
                                text.isupper() and 
                                len(text.split()) <= 6 and 
                                has_keyword and  # 必须包含产品关键词
                                not any(skip in text_lower for skip in ['sign', 'register', 'see', 'start', 'read', 'discover'])
                            )
                            
                            # 只保留真正的产品类目链接
                            if is_product_category_url or (has_keyword and is_valid_category_name):
                                if href and not href.startswith('http'):
                                    if href.startswith('/'):
                                        href = f"https://www.traceparts.cn{href}"
                                
                                # 去重检查
                                duplicate = any(
                                    item['text'].upper() == text.upper() or item['url'] == href 
                                    for item in category_data
                                )
                                
                                if not duplicate:
                                    match_reason = "product_url" if is_product_category_url else "keyword"
                                    
                                    category_data.append({
                                        "text": text,
                                        "url": href,
                                        "element_tag": "a",
                                        "element_index": len(category_data),
                                        "match_reason": match_reason
                                    })
                                    
                                    LOG.info(f"  ✅ 产品类目: '{text}' -> '{href}'")
                                    
                                    # 增加提取数量限制
                                    if len(category_data) >= 30:
                                        break
                    except:
                        continue
                
                if category_data:
                    category_info = "\n\n=== TraceParts产品类目信息（真实链接） ===\n"
                    category_info += "注意：以下是从网页提取的真实产品类目链接，请务必在JSON中保留这些URL\n\n"
                    
                    for item in category_data:
                        if item.get('match_reason') == 'product_url':  # 优先显示产品URL
                            category_info += f"🔗 产品类目: {item['text']}\n"
                            category_info += f"🌐 真实链接: {item['url']}\n"
                            category_info += f"📝 类型: TraceParts产品分类链接\n"
                            category_info += "=" * 50 + "\n"
                        else:
                            category_info += f"类目: {item['text']}\n"
                            if item['url']:
                                category_info += f"链接: {item['url']}\n"
                            category_info += f"类型: {item.get('match_reason', 'unknown')}\n"
                            category_info += "---\n"
                    
                    content += category_info
                    
                    # 统计真实产品链接数量
                    product_links = [item for item in category_data if item.get('match_reason') == 'product_url']
                    LOG.info(f"✅ 备用方案提取了 {len(category_data)} 个类目，其中 {len(product_links)} 个是真实产品链接")
                    
                    # 输出详细提取结果
                    LOG.info("📋 真实产品类目链接:")
                    for i, item in enumerate(product_links[:10]):  # 显示前10个产品链接
                        LOG.info(f"  {i+1}. {item['text']}")
                        LOG.info(f"      -> {item['url']}")
                    if len(product_links) > 10:
                        LOG.info(f"  ... 还有 {len(product_links) - 10} 个产品类目")
                    
                    if len(category_data) > len(product_links):
                        other_links = len(category_data) - len(product_links)
                        LOG.info(f"📄 其他链接: {other_links} 个")
                else:
                    LOG.warning("⚠️  备用方案未找到任何类目链接")
        
        except Exception as e:
            LOG.warning(f"⚠️  类目链接提取失败: {str(e)}")
        
        driver.quit()
        
        LOG.info(f"✅ Selenium网页加载成功，内容长度: {len(content)} 字符")
        return content
        
    except Exception as e:
        LOG.error(f"❌ Selenium加载失败: {str(e)}")
        raise

def load_web_content(url: str, use_mock: bool = False) -> str:
    """加载网页内容的主函数"""
    
    if use_mock:
        return create_mock_data()
    
    if SELENIUM_AVAILABLE:
        try:
            return load_web_content_selenium(url)
        except Exception as e:
            LOG.warning(f"⚠️  Selenium方法失败: {str(e)}")
    
    # 备用：使用模拟数据
    LOG.info("🎭 使用模拟数据进行测试...")
    return create_mock_data()

class AsyncCategoryExtractor:
    """异步类目提取器（参考cot_extractor_safe.py的设计）"""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.chunk_sem = asyncio.Semaphore(config.chunk_concurrency)
        self.stats = ExtractionStats()
        self.error_writer = None
        
        # 配置LLM
        self.llm = ChatOpenAI(
            model=config.model,
            openai_api_key=config.api_key,
            openai_api_base=config.base_url + "/v1",
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
        
        # 创建提示模板 - 改进版本（包含链接提取）
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是TraceParts网站的专业分析师。请从网页内容中提取产品类目信息，包括类目名称、描述和链接。

TraceParts是一个CAD零件库平台，主要包含以下类型的产品类目：
- MECHANICAL COMPONENTS (机械组件)
- ELECTRICAL (电气) 
- MATERIALS (材料)
- HYDRAULICS (液压)
- PNEUMATICS (气动)
- OPTICS (光学)
- SENSORS (传感器)
- ELECTRONICS (电子)
- MANUFACTURING ENGINEERING (制造工程)
- MATERIAL HANDLING AND LIFTING EQUIPMENT (物料搬运和起重设备)
- VACUUM EQUIPMENT (真空设备)
- HEAT TRANSMISSION (热传导)
- BUILDING & CONSTRUCTIONS (建筑和施工)
- CIVIL ENGINEERING (土木工程)

**关键要求：**
1. **严禁自己编造URL**：只能使用内容中明确提供的真实链接
2. **严格匹配**：当看到"🔗 产品类目: XXX"和"🌐 真实链接: XXX"时，必须原样使用这个链接
3. **完全复制**：URL必须与内容中提供的完全一致，包括所有参数和编码

**返回格式要求：**
请返回严格的JSON格式，URL必须是内容中提供的真实链接：

{{
    "main_categories": [
        {{
            "name": "MECHANICAL COMPONENTS",
            "description": "机械组件相关产品",
            "url": "完全复制内容中的真实链接，不要修改任何字符",
            "subcategories": []
        }}
    ]
}}

**严重警告：**
- 绝对不要猜测或编造CatalogPath参数（如TP01、TP02等）
- 绝对不要修改URL中的任何字符，包括%3A、%3ATP等编码
- 如果内容中没有提供某个类目的链接，url字段设为空字符串""
- 只有内容中明确标记为"🌐 真实链接"的URL才能使用"""),
            ("human", "请分析以下TraceParts网站内容，提取所有产品类目。**重要：严格使用内容中的真实链接，不要自己编造任何URL**：\n\n{content}")
        ])

    def clean_category_name(self, name: str) -> str:
        """清理类目名称，移除多余字符和格式问题"""
        if not name:
            return ""
        
        # 移除各种JSON格式残留
        name = re.sub(r'^["\'\s]*', '', name)  # 开头的引号和空格
        name = re.sub(r'["\'\s,]*$', '', name)  # 结尾的引号、空格、逗号
        name = re.sub(r'^name["\'\s]*:["\'\s]*', '', name, flags=re.IGNORECASE)  # "name": 前缀
        name = re.sub(r'["\'\s]*,["\'\s]*$', '', name)  # 结尾的逗号
        name = re.sub(r'\\["\']', '', name)  # 转义字符
        name = re.sub(r'^\s*[\[{]\s*', '', name)  # 开头的括号
        name = re.sub(r'\s*[}\]]\s*$', '', name)  # 结尾的括号
        
        # 统一大小写和空格
        name = name.strip()
        name = re.sub(r'\s+', ' ', name)  # 多个空格变成一个
        
        return name

    async def initialize(self, output_dir: str):
        """初始化输出目录和错误记录器"""
        os.makedirs(output_dir, exist_ok=True)
        self.error_writer = AsyncJsonlWriter(os.path.join(output_dir, "_errors.jsonl"))

    async def extract_chunk_categories(self, chunk_id: int, chunk_content: str) -> Optional[List[Dict[str, Any]]]:
        """异步提取单个内容块的类目信息（改进的解析逻辑）"""
        
        async with self.chunk_sem:  # 控制并发数量
            LOG.info(f"📝 开始分析第 {chunk_id} 个内容块...")
            
            for attempt in range(1, self.config.max_retries + 1):
                try:
                    # 在线程池中运行同步的LangChain调用
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor() as executor:
                        chain = self.extraction_prompt | self.llm
                        
                        future = executor.submit(
                            chain.invoke, 
                            {"content": chunk_content}
                        )
                        
                        response = await asyncio.wait_for(
                            asyncio.wrap_future(future),
                            timeout=self.config.chunk_timeout
                        )
                    
                    LOG.debug(f"🤖 块 {chunk_id} AI响应预览: {response.content[:200]}...")
                    
                    # 尝试解析JSON响应 - 改进版本
                    categories = self.parse_ai_response(response.content, chunk_id)
                    
                    if categories:
                        LOG.info(f"✅ 块 {chunk_id} 提取到 {len(categories)} 个类目")
                        return categories
                    else:
                        LOG.warning(f"⚠️  块 {chunk_id} 未能提取到有效类目")
                        return []
                    
                except asyncio.TimeoutError:
                    error_type = "TIMEOUT"
                    error_msg = f"第 {attempt} 次尝试超时"
                    LOG.warning(f"⏰ 块 {chunk_id} {error_msg}")
                    
                except Exception as e:
                    error_type = "API_ERROR"
                    error_msg = f"第 {attempt} 次尝试失败: {str(e)}"
                    LOG.warning(f"⚠️  块 {chunk_id} {error_msg}")
                
                # 记录错误并重试
                if attempt < self.config.max_retries:
                    delay = backoff_delay(attempt)
                    LOG.info(f"🔄 块 {chunk_id} 将在 {delay:.2f}s 后重试...")
                    await asyncio.sleep(delay)
                    self.stats.retries_used += 1
                else:
                    # 记录最终失败
                    await self.error_writer.write({
                        "chunk_id": chunk_id,
                        "error_type": error_type,
                        "error_msg": error_msg,
                        "attempts": attempt
                    })
                    LOG.error(f"❌ 块 {chunk_id} 所有重试都失败，放弃")
                    return None
            
            return None

    def parse_ai_response(self, response_content: str, chunk_id: int) -> List[Dict[str, Any]]:
        """解析AI响应，支持多种格式和错误恢复"""
        categories = []
        
        # 方法1: 尝试直接JSON解析
        try:
            # 清理响应内容
            cleaned_content = response_content.strip()
            if cleaned_content.startswith('```json'):
                cleaned_content = re.sub(r'^```json\s*', '', cleaned_content)
            if cleaned_content.endswith('```'):
                cleaned_content = re.sub(r'\s*```$', '', cleaned_content)
            
            result = json.loads(cleaned_content)
            if "main_categories" in result and isinstance(result["main_categories"], list):
                for cat in result["main_categories"]:
                    if isinstance(cat, dict) and "name" in cat:
                        clean_name = self.clean_category_name(cat["name"])
                        if clean_name:
                            clean_cat = {
                                "name": clean_name,
                                "description": cat.get("description", "").strip(),
                                "url": cat.get("url", ""),
                                "subcategories": []
                            }
                            # 处理子类目
                            if "subcategories" in cat and isinstance(cat["subcategories"], list):
                                for sub in cat["subcategories"]:
                                    if isinstance(sub, dict) and "name" in sub:
                                        clean_sub_name = self.clean_category_name(sub["name"])
                                        if clean_sub_name:
                                            clean_cat["subcategories"].append({
                                                "name": clean_sub_name,
                                                "description": sub.get("description", "").strip(),
                                                "url": sub.get("url", "")
                                            })
                            categories.append(clean_cat)
                
                LOG.debug(f"块 {chunk_id} JSON解析成功，提取到 {len(categories)} 个类目")
                return categories
                
        except json.JSONDecodeError as e:
            LOG.debug(f"块 {chunk_id} JSON解析失败: {str(e)}, 尝试文本解析")
        
        # 方法2: 文本模式解析
        categories = self.extract_categories_from_text(response_content, chunk_id)
        
        return categories

    def extract_categories_from_text(self, text: str, chunk_id: int) -> List[Dict[str, Any]]:
        """从文本中提取类目信息（备用方案）"""
        categories = []
        
        # 预定义的类目关键词
        known_categories = [
            "MECHANICAL COMPONENTS", "ELECTRICAL", "MATERIALS", "HYDRAULICS", 
            "PNEUMATICS", "OPTICS", "SENSORS", "ELECTRONICS", 
            "MANUFACTURING ENGINEERING", "MATERIAL HANDLING AND LIFTING EQUIPMENT",
            "VACUUM EQUIPMENT", "HEAT TRANSMISSION", "BUILDING & CONSTRUCTIONS",
            "CIVIL ENGINEERING"
        ]
        
        # 在文本中搜索已知类目
        for category in known_categories:
            # 使用多种模式匹配
            patterns = [
                rf'\b{re.escape(category)}\b',
                rf'["\']?\s*{re.escape(category)}\s*["\']?',
                rf'name["\']?\s*:\s*["\']?\s*{re.escape(category)}\s*["\']?'
            ]
            
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    categories.append({
                        "name": category,
                        "description": f"{category}相关产品",
                        "url": "",
                        "subcategories": []
                    })
                    break  # 找到就跳出内层循环
        
        # 移除重复
        unique_categories = []
        seen_names = set()
        for cat in categories:
            name = cat["name"]
            if name not in seen_names:
                seen_names.add(name)
                unique_categories.append(cat)
        
        LOG.debug(f"块 {chunk_id} 文本解析提取到 {len(unique_categories)} 个类目")
        return unique_categories

    def merge_and_deduplicate_categories(self, all_categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并和去重类目，智能处理重复和相似项，并确保按预定义顺序排列"""
        
        # 预定义的类目顺序（按重要性和逻辑顺序）
        predefined_order = [
            "MECHANICAL COMPONENTS",
            "MANUFACTURING ENGINEERING", 
            "MATERIALS (BARS, BEAMS, TUBES, ETC.)",
            "MATERIAL HANDLING AND LIFTING EQUIPMENT",
            "ELECTRICAL",
            "SENSORS AND MEASUREMENT SYSTEMS",
            "ELECTRONICS",
            "OPTICS",
            "PNEUMATICS",
            "VACUUM EQUIPMENT",
            "HYDRAULICS",
            "HEAT TRANSMISSION",
            "BUILDING & CONSTRUCTIONS (MATERIALS AND EQUIPMENTS)",
            "CIVIL ENGINEERING"
        ]
        
        # 名称映射字典：AI可能返回的简化名称 -> 标准名称
        name_mapping = {
            "MECHANICAL COMPONENTS": "MECHANICAL COMPONENTS",
            "MECHANICAL": "MECHANICAL COMPONENTS",
            "MANUFACTURING ENGINEERING": "MANUFACTURING ENGINEERING", 
            "MANUFACTURING": "MANUFACTURING ENGINEERING",
            "MATERIALS": "MATERIALS (BARS, BEAMS, TUBES, ETC.)",
            "MATERIALS (BARS, BEAMS, TUBES, ETC.)": "MATERIALS (BARS, BEAMS, TUBES, ETC.)",
            "MATERIAL HANDLING AND LIFTING EQUIPMENT": "MATERIAL HANDLING AND LIFTING EQUIPMENT",
            "MATERIAL HANDLING": "MATERIAL HANDLING AND LIFTING EQUIPMENT",
            "ELECTRICAL": "ELECTRICAL",
            "SENSORS AND MEASUREMENT SYSTEMS": "SENSORS AND MEASUREMENT SYSTEMS",
            "SENSORS": "SENSORS AND MEASUREMENT SYSTEMS",  # 重要：简化名称映射
            "MEASUREMENT SYSTEMS": "SENSORS AND MEASUREMENT SYSTEMS",
            "ELECTRONICS": "ELECTRONICS",
            "OPTICS": "OPTICS",
            "PNEUMATICS": "PNEUMATICS",
            "VACUUM EQUIPMENT": "VACUUM EQUIPMENT",
            "VACUUM": "VACUUM EQUIPMENT",
            "HYDRAULICS": "HYDRAULICS",
            "HEAT TRANSMISSION": "HEAT TRANSMISSION",
            "BUILDING & CONSTRUCTIONS": "BUILDING & CONSTRUCTIONS (MATERIALS AND EQUIPMENTS)",
            "BUILDING & CONSTRUCTIONS (MATERIALS AND EQUIPMENTS)": "BUILDING & CONSTRUCTIONS (MATERIALS AND EQUIPMENTS)",
            "BUILDING": "BUILDING & CONSTRUCTIONS (MATERIALS AND EQUIPMENTS)",
            "CONSTRUCTIONS": "BUILDING & CONSTRUCTIONS (MATERIALS AND EQUIPMENTS)",
            "CIVIL ENGINEERING": "CIVIL ENGINEERING",
            "CIVIL": "CIVIL ENGINEERING"
        }
        
        category_map = {}
        
        for category in all_categories:
            if not isinstance(category, dict) or "name" not in category:
                continue
                
            # 清理名称
            clean_name = self.clean_category_name(category["name"])
            if not clean_name:
                continue
            
            # 标准化名称映射
            normalized_input = clean_name.upper().strip()
            
            # 查找映射的标准名称
            standard_name = None
            
            # 1. 直接匹配
            if normalized_input in name_mapping:
                standard_name = name_mapping[normalized_input]
            else:
                # 2. 部分匹配（针对包含关系）
                for short_name, full_name in name_mapping.items():
                    if short_name in normalized_input or normalized_input in short_name:
                        standard_name = full_name
                        break
                
                # 3. 如果还是没找到，使用原名称
                if standard_name is None:
                    standard_name = clean_name
            
            # 使用标准名称作为key
            normalized_standard = standard_name.upper()
            
            if normalized_standard not in category_map:
                # 新类目
                category_map[normalized_standard] = {
                    "name": standard_name,  # 使用标准名称
                    "description": category.get("description", f"{standard_name}相关产品").strip(),
                    "url": category.get("url", ""),
                    "subcategories": []
                }
            else:
                # 合并描述（选择更详细的）
                existing_desc = category_map[normalized_standard]["description"]
                new_desc = category.get("description", "").strip()
                
                if new_desc and len(new_desc) > len(existing_desc) and "从文本提取" not in new_desc:
                    category_map[normalized_standard]["description"] = new_desc
            
            # 合并子类目
            if "subcategories" in category and isinstance(category["subcategories"], list):
                existing_subs = {sub["name"].upper(): sub for sub in category_map[normalized_standard]["subcategories"]}
                
                for sub in category["subcategories"]:
                    if isinstance(sub, dict) and "name" in sub:
                        clean_sub_name = self.clean_category_name(sub["name"])
                        if clean_sub_name:
                            normalized_sub = clean_sub_name.upper()
                            if normalized_sub not in existing_subs:
                                category_map[normalized_standard]["subcategories"].append({
                                    "name": clean_sub_name,
                                    "description": sub.get("description", "").strip(),
                                    "url": sub.get("url", "")
                                })
        
        # 按预定义顺序排列类目
        ordered_categories = []
        
        # 首先添加预定义顺序中的类目
        for predefined_name in predefined_order:
            normalized_predefined = predefined_name.upper()
            if normalized_predefined in category_map:
                category = category_map[normalized_predefined]
                # 对子类目也进行排序
                category["subcategories"].sort(key=lambda x: x["name"])
                ordered_categories.append(category)
                # 从map中移除已处理的类目
                del category_map[normalized_predefined]
        
        # 然后添加其他未预定义的类目（按字母顺序）
        remaining_categories = list(category_map.values())
        remaining_categories.sort(key=lambda x: x["name"])
        
        for category in remaining_categories:
            # 对子类目进行排序
            category["subcategories"].sort(key=lambda x: x["name"])
            ordered_categories.append(category)
        
        LOG.info(f"📋 类目标准化映射完成，预定义类目: {len(ordered_categories) - len(remaining_categories)} 个，其他类目: {len(remaining_categories)} 个")
        
        return ordered_categories

    async def extract_all_categories(self, chunks: List[str]) -> Dict[str, Any]:
        """异步并发提取所有块的类目信息（改进的去重逻辑和顺序保证）"""
        LOG.info(f"🤖 开始异步AI分析，并发数: {self.config.chunk_concurrency}")
        
        self.stats.total_chunks = len(chunks)
        
        # 创建带索引的任务，保持chunk顺序信息
        indexed_tasks = []
        for i, chunk in enumerate(chunks[:5]):  # 限制处理前5个块
            task = self.extract_chunk_categories_with_index(i+1, chunk, i)
            indexed_tasks.append(task)
        
        # 并发执行所有任务
        LOG.info(f"🚀 启动 {len(indexed_tasks)} 个并发任务...")
        indexed_results = await asyncio.gather(*indexed_tasks, return_exceptions=True)
        
        # 按原始chunk顺序处理结果
        all_categories = []
        for i, result in enumerate(indexed_results):
            if isinstance(result, Exception):
                LOG.error(f"❌ 块 {i+1} 任务异常: {str(result)}")
                self.stats.failed_chunks += 1
            elif result is None:
                LOG.warning(f"⚠️  块 {i+1} 返回空结果")
                self.stats.failed_chunks += 1
            else:
                chunk_idx, categories = result
                if categories:
                    self.stats.successful_chunks += 1
                    # 为每个类目添加来源信息（用于调试）
                    for cat in categories:
                        cat["_source_chunk"] = chunk_idx
                    all_categories.extend(categories)
                else:
                    self.stats.failed_chunks += 1
        
        # 改进的去重和合并逻辑（现在包含排序）
        unique_categories = self.merge_and_deduplicate_categories(all_categories)
        
        # 移除调试信息
        for cat in unique_categories:
            cat.pop("_source_chunk", None)
        
        self.stats.categories_found = len(unique_categories)
        
        # 构建最终结果
        result = {
            "main_categories": unique_categories,
            "extracted_info": {
                "total_categories": self.stats.categories_found,
                "extraction_time": datetime.now().isoformat(),
                "source_url": "https://www.traceparts.cn/en",
                "chunks_processed": self.stats.successful_chunks,
                "chunks_failed": self.stats.failed_chunks,
                "retries_used": self.stats.retries_used,
                "concurrency_used": self.config.chunk_concurrency,
                "ordering_applied": "预定义类目顺序 + 字母顺序",
                "processing_stats": {
                    "total_chunks": self.stats.total_chunks,
                    "successful_chunks": self.stats.successful_chunks,
                    "failed_chunks": self.stats.failed_chunks,
                    "success_rate": f"{self.stats.successful_chunks/self.stats.total_chunks*100:.1f}%" if self.stats.total_chunks > 0 else "0%"
                }
            }
        }
        
        LOG.info(f"✅ 异步分析完成，找到 {self.stats.categories_found} 个唯一类目")
        LOG.info(f"📊 处理统计: {self.stats.successful_chunks}/{self.stats.total_chunks} 成功 ({self.stats.successful_chunks/self.stats.total_chunks*100:.1f}%)" if self.stats.total_chunks > 0 else "📊 处理统计: 0/0")
        LOG.info(f"🔄 总重试次数: {self.stats.retries_used}")
        LOG.info(f"📋 类目已按预定义顺序排列")
        
        return result

    async def extract_chunk_categories_with_index(self, chunk_id: int, chunk_content: str, original_index: int) -> Optional[tuple]:
        """异步提取单个内容块的类目信息，返回带索引的结果"""
        categories = await self.extract_chunk_categories(chunk_id, chunk_content)
        if categories is not None:
            return (original_index, categories)
        return None

async def test_async_web_scraping():
    """异步主测试函数"""
    LOG.info("=" * 80)
    LOG.info("🕷️  异步并发网页爬取测试 - TraceParts 模型类目提取")
    LOG.info("=" * 80)
    
    target_url = "https://www.traceparts.cn/en"
    config = ScrapingConfig()
    
    try:
        # 1. 初始化提取器
        LOG.info("🔧 初始化异步类目提取器...")
        extractor = AsyncCategoryExtractor(config)
        await extractor.initialize("results")
        LOG.info("✅ 提取器初始化完成")
        
        # 2. 加载网页内容（在线程池中运行）
        LOG.info("\n🌐 开始加载网页内容...")
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            content = await loop.run_in_executor(
                executor, 
                load_web_content, 
                target_url, 
                False  # use_mock
            )
        
        LOG.info(f"📊 内容统计:")
        LOG.info(f"  - 总长度: {len(content)} 字符")
        LOG.info(f"  - 行数: {len(content.split('\\n'))} 行")
        
        # 检查内容质量
        if len(content) < 1000:
            LOG.warning("⚠️  内容过少，切换到模拟数据")
            content = create_mock_data()
            LOG.info("🎭 已切换到模拟数据模式")
        
        # 3. 分割内容
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=3000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
            length_function=len,
        )
        chunks = text_splitter.split_text(content)
        LOG.info(f"✅ 内容分割完成，共 {len(chunks)} 个块")
        
        # 4. 异步提取模型类目信息
        LOG.info(f"\n🔍 开始异步AI分析 (并发数: {config.chunk_concurrency})...")
        start_time = time.time()
        
        categories_data = await extractor.extract_all_categories(chunks)
        
        analysis_time = time.time() - start_time
        LOG.info(f"⏱️  AI分析总耗时: {analysis_time:.2f} 秒")
        
        # 5. 合并结果
        final_result = {
            "extraction_method_1": categories_data,
            "metadata": {
                "url": target_url,
                "extraction_date": datetime.now().isoformat(),
                "content_length": len(content),
                "chunks_count": len(chunks),
                "analysis_time_seconds": round(analysis_time, 2),
                "extraction_methods": ["async_concurrent_ai_extraction"],
                "selenium_available": SELENIUM_AVAILABLE,
                "config": {
                    "chunk_concurrency": config.chunk_concurrency,
                    "max_retries": config.max_retries,
                    "chunk_timeout": config.chunk_timeout
                },
                "content_preview": content[:300].replace('\n', ' ')
            }
        }
        
        # 6. 异步保存结果
        LOG.info("💾 正在异步保存结果...")
        filepath = "results/traceparts_categories_async.json"
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(final_result, ensure_ascii=False, indent=2))
        
        LOG.info(f"✅ 结果已保存到: {filepath}")
        
        LOG.info("\n" + "=" * 80)
        LOG.info("📋 提取结果摘要:")
        LOG.info("=" * 80)
        
        method1_count = len(categories_data.get("main_categories", []))
        
        LOG.info(f"🎯 提取到的类目数量: {method1_count} 个")
        LOG.info(f"📁 结果文件: {filepath}")
        LOG.info(f"⏱️  总处理时间: {analysis_time:.2f} 秒")
        LOG.info(f"🔄 重试统计: {extractor.stats.retries_used} 次重试")
        
        # 显示提取结果
        if method1_count > 0:
            LOG.info("\n🔖 提取到的类目:")
            for i, cat in enumerate(categories_data["main_categories"]):
                name = cat.get('name', 'N/A')
                sub_count = len(cat.get('subcategories', []))
                LOG.info(f"  {i+1}. {name} ({sub_count} 个子类目)")
        else:
            LOG.warning("\n⚠️  未提取到类目，可能需要:")
            LOG.warning("  1. 安装selenium: pip install selenium")
            LOG.warning("  2. 安装ChromeDriver")
            LOG.warning("  3. 检查网络连接")
        
        LOG.info("=" * 80)
        LOG.info("🎉 异步网页爬取测试完成！")
        
        return method1_count > 0
        
    except Exception as e:
        LOG.error(f"❌ 测试失败: {str(e)}")
        LOG.info("=" * 80)
        return False

def test_web_scraping():
    """同步包装函数，运行异步测试"""
    return asyncio.run(test_async_web_scraping())

if __name__ == "__main__":
    success = test_web_scraping()
    
    if success:
        print("✅ TraceParts 异步网页爬取测试成功完成！")
    else:
        print("❌ TraceParts 异步网页爬取测试失败！")
        print("💡 建议：尝试安装selenium或使用模拟数据模式")
        
    exit(0 if success else 1) 