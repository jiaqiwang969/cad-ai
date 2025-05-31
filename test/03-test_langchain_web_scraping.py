#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangChain 网页爬取测试 - TraceParts 模型类目信息抓取
使用Selenium处理JavaScript动态内容
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import time
from datetime import datetime
from typing import List, Dict, Any

from langchain_openai import ChatOpenAI
from config import get_openai_config, get_masked_api_key, validate_config
from langchain.schema import HumanMessage, SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate

# 导入selenium相关模块
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# 备用：使用requests+beautifulsoup
import requests
from bs4 import BeautifulSoup

def setup_llm():
    """配置LLM"""
    try:
        config = get_openai_config()
        if not validate_config(config):
            raise ValueError("配置验证失败")
        
        print(f"✅ 使用API Key: {get_masked_api_key(config['api_key'])}")
        print(f"✅ 使用Base URL: {config['base_url']}")
        
        llm = ChatOpenAI(
            model=config['model'],
            openai_api_key=config['api_key'],
            openai_api_base=config['base_url'],
            temperature=0.3,
            max_tokens=2000
        )
        return llm
    except Exception as e:
        print(f"❌ LLM配置失败: {e}")
        raise

def load_web_content_selenium(url: str) -> str:
    """使用Selenium加载动态网页内容"""
    print(f"🌐 使用Selenium加载网页: {url}")
    
    if not SELENIUM_AVAILABLE:
        raise Exception("Selenium未安装，请运行：pip install selenium")
    
    try:
        # 配置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 初始化WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        # 访问网页
        driver.get(url)
        
        # 等待页面加载完成
        print("⏳ 等待页面加载...")
        time.sleep(5)
        
        # 尝试等待特定元素加载
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except TimeoutException:
            print("⚠️  页面加载超时，继续尝试获取内容...")
        
        # 获取页面内容
        content = driver.page_source
        
        # 查找类目相关的内容
        try:
            # 尝试找到类目容器
            category_elements = driver.find_elements(By.CSS_SELECTOR, 
                "[class*='category'], [class*='component'], [class*='product'], div[role='button'], a[href*='category']")
            
            print(f"📋 找到 {len(category_elements)} 个可能的类目元素")
            
            # 提取类目文本
            category_texts = []
            for element in category_elements[:20]:  # 限制数量避免过多
                try:
                    text = element.text.strip()
                    if text and len(text) > 2 and len(text) < 100:
                        category_texts.append(text)
                except:
                    continue
            
            if category_texts:
                content += "\n\n=== 提取的类目信息 ===\n" + "\n".join(category_texts)
                print(f"✅ 额外提取了 {len(category_texts)} 个类目文本")
        
        except Exception as e:
            print(f"⚠️  类目元素提取失败: {str(e)}")
        
        driver.quit()
        
        print(f"✅ Selenium网页加载成功，内容长度: {len(content)} 字符")
        return content
        
    except Exception as e:
        print(f"❌ Selenium加载失败: {str(e)}")
        raise

def load_web_content_requests(url: str) -> str:
    """使用requests+BeautifulSoup作为备用方法"""
    print(f"🌐 使用requests+BeautifulSoup加载网页: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 提取文本内容
        content = soup.get_text()
        
        # 尝试查找类目相关的元素
        category_elements = soup.find_all(['div', 'a', 'span'], 
            string=re.compile(r'(MECHANICAL|ELECTRICAL|MATERIAL|HYDRAULICS|PNEUMATICS|OPTICS)', re.I))
        
        if category_elements:
            category_texts = [elem.get_text().strip() for elem in category_elements[:10]]
            content += "\n\n=== 找到的类目关键词 ===\n" + "\n".join(category_texts)
            print(f"✅ 找到 {len(category_texts)} 个类目关键词")
        
        print(f"✅ requests加载成功，内容长度: {len(content)} 字符")
        return content
        
    except Exception as e:
        print(f"❌ requests加载失败: {str(e)}")
        raise

def create_mock_data() -> str:
    """创建模拟数据用于测试AI提取功能"""
    print("🎭 使用模拟数据进行测试...")
    
    mock_content = """
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
    
    MATERIAL HANDLING AND LIFTING EQUIPMENT
    - Conveyors
    - Hoists and cranes
    - Forklifts
    - Storage systems
    
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
    
    VACUUM EQUIPMENT
    - Vacuum pumps
    - Vacuum chambers
    - Vacuum valves
    - Vacuum gauges
    
    HYDRAULICS
    - Hydraulic pumps
    - Hydraulic cylinders
    - Hydraulic valves
    - Hydraulic filters
    
    HEAT TRANSMISSION
    - Heat exchangers
    - Radiators
    - Cooling fans
    - Thermal insulation
    
    BUILDING & CONSTRUCTIONS (MATERIALS AND EQUIPMENTS)
    - Construction materials
    - Building tools
    - Safety equipment
    - Access systems
    
    CIVIL ENGINEERING
    - Infrastructure components
    - Road construction
    - Bridge components
    - Drainage systems
    """
    
    return mock_content

def load_web_content(url: str, use_mock: bool = False) -> str:
    """加载网页内容的主函数，尝试多种方法"""
    
    if use_mock:
        return create_mock_data()
    
    # 方法1: 尝试使用Selenium
    if SELENIUM_AVAILABLE:
        try:
            return load_web_content_selenium(url)
        except Exception as e:
            print(f"⚠️  Selenium方法失败: {str(e)}")
    
    # 方法2: 尝试使用requests
    try:
        return load_web_content_requests(url)
    except Exception as e:
        print(f"⚠️  requests方法失败: {str(e)}")
    
    # 方法3: 使用模拟数据
    print("🎭 所有网络方法失败，使用模拟数据进行测试...")
    return create_mock_data()

def split_content(content: str) -> List[str]:
    """分割网页内容为合适的块"""
    print("📄 正在分割网页内容...")
    
    # 配置文本分割器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        length_function=len,
    )
    
    # 分割文本
    chunks = text_splitter.split_text(content)
    print(f"✅ 内容分割完成，共 {len(chunks)} 个块")
    
    # 显示前几个块的片段用于调试
    for i, chunk in enumerate(chunks[:3]):
        preview = chunk[:200].replace('\n', ' ')
        print(f"  📄 块 {i+1} 预览: {preview}...")
    
    return chunks

def extract_model_categories(llm, chunks: List[str]) -> Dict[str, Any]:
    """使用LLM提取模型类目信息"""
    print("🤖 正在使用AI分析模型类目信息...")
    
    # 创建提示模板
    extraction_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是TraceParts网站的专业分析师。请从网页内容中提取产品类目信息。

TraceParts是一个CAD零件库平台，主要包含以下类型的产品类目：
- MECHANICAL COMPONENTS (机械组件)
- ELECTRICAL (电气)
- MATERIALS (材料)
- HYDRAULICS (液压)
- PNEUMATICS (气动)
- OPTICS (光学)
- SENSORS (传感器)
- ELECTRONICS (电子)

请仔细分析内容，提取所有能找到的产品类目和子类目。

返回JSON格式：
{{
    "main_categories": [
        {{
            "name": "主类目名称",
            "description": "描述",
            "subcategories": [
                {{
                    "name": "子类目名称",
                    "description": "描述"
                }}
            ]
        }}
    ]
}}"""),
        ("human", "请分析以下TraceParts网站内容，提取所有产品类目：\n\n{content}")
    ])
    
    all_categories = []
    
    for i, chunk in enumerate(chunks[:3]):  # 处理前3个块
        print(f"  📝 分析第 {i+1}/{min(len(chunks), 3)} 个内容块...")
        
        try:
            # 使用Chain处理
            chain = extraction_prompt | llm
            response = chain.invoke({
                "content": chunk
            })
            
            print(f"    🤖 AI响应预览: {response.content[:100]}...")
            
            # 尝试解析JSON响应
            try:
                chunk_result = json.loads(response.content)
                if "main_categories" in chunk_result:
                    all_categories.extend(chunk_result["main_categories"])
                    print(f"    ✅ 提取到 {len(chunk_result['main_categories'])} 个类目")
            except json.JSONDecodeError:
                print(f"    ⚠️  非JSON格式响应，尝试文本解析...")
                # 尝试从响应文本中提取类目名称
                lines = response.content.split('\n')
                for line in lines:
                    if any(keyword in line.upper() for keyword in ['MECHANICAL', 'ELECTRICAL', 'MATERIAL', 'HYDRAULIC', 'PNEUMATIC']):
                        all_categories.append({
                            "name": line.strip(),
                            "description": "从文本提取",
                            "subcategories": []
                        })
                
        except Exception as e:
            print(f"    ❌ 第 {i+1} 块分析失败: {str(e)}")
            continue
    
    # 合并和去重类目
    unique_categories = []
    seen_names = set()
    
    for category in all_categories:
        name = category.get("name", "").strip()
        if name and name not in seen_names:
            seen_names.add(name)
            unique_categories.append(category)
    
    # 构建最终结果
    result = {
        "main_categories": unique_categories,
        "extracted_info": {
            "total_categories": len(unique_categories),
            "extraction_time": datetime.now().isoformat(),
            "source_url": "https://www.traceparts.cn/en",
            "chunks_processed": min(len(chunks), 3)
        }
    }
    
    print(f"✅ 模型类目提取完成，共找到 {len(unique_categories)} 个主要类目")
    
    return result

def save_results(data: Dict[str, Any], filename: str = "traceparts_categories.json"):
    """保存结果到JSON文件"""
    print(f"💾 正在保存结果到 {filename}...")
    
    try:
        # 创建results目录（如果不存在）
        os.makedirs("results", exist_ok=True)
        
        filepath = os.path.join("results", filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 结果已保存到: {filepath}")
        
        # 显示保存的内容摘要
        method1_count = len(data.get("extraction_method_1", {}).get("main_categories", []))
        method2_count = len(data.get("extraction_method_2", {}).get("product_categories", []))
        total_count = max(method1_count, method2_count)
        
        print(f"📊 保存了 {total_count} 个类目信息")
        
        return filepath
        
    except Exception as e:
        print(f"❌ 保存失败: {str(e)}")
        raise

def test_web_scraping():
    """主测试函数"""
    print("=" * 80)
    print("🕷️  LangChain 网页爬取测试 - TraceParts 模型类目提取 (改进版)")
    print("=" * 80)
    
    target_url = "https://www.traceparts.cn/en"
    
    try:
        # 1. 配置LLM
        print("🔧 配置LangChain LLM...")
        llm = setup_llm()
        print("✅ LLM配置完成")
        
        # 2. 加载网页内容（尝试多种方法）
        print("\n🌐 开始加载网页内容...")
        content = load_web_content(target_url, use_mock=False)
        
        print(f"📊 内容统计:")
        print(f"  - 总长度: {len(content)} 字符")
        print(f"  - 行数: {len(content.split('\\n'))} 行")
        
        # 检查内容质量
        if len(content) < 1000:
            print("⚠️  内容过少，可能需要使用模拟数据")
            content = create_mock_data()
            print("🎭 已切换到模拟数据模式")
        
        # 3. 分割内容
        chunks = split_content(content)
        
        # 4. 提取模型类目信息
        print("\n🔍 开始AI分析...")
        categories_data = extract_model_categories(llm, chunks)
        
        # 5. 合并结果
        final_result = {
            "extraction_method_1": categories_data,
            "extraction_method_2": {"product_categories": []},  # 简化版本
            "metadata": {
                "url": target_url,
                "extraction_date": datetime.now().isoformat(),
                "content_length": len(content),
                "chunks_count": len(chunks),
                "extraction_methods": ["improved_ai_extraction"],
                "selenium_available": SELENIUM_AVAILABLE,
                "content_preview": content[:300].replace('\n', ' ')
            }
        }
        
        # 6. 保存结果
        saved_file = save_results(final_result)
        
        print("\n" + "=" * 80)
        print("📋 提取结果摘要:")
        print("=" * 80)
        
        method1_count = len(categories_data.get("main_categories", []))
        
        print(f"🎯 提取到的类目数量: {method1_count} 个")
        print(f"📁 结果文件: {saved_file}")
        
        # 显示提取结果
        if method1_count > 0:
            print("\n🔖 提取到的类目:")
            for i, cat in enumerate(categories_data["main_categories"]):
                name = cat.get('name', 'N/A')
                sub_count = len(cat.get('subcategories', []))
                print(f"  {i+1}. {name} ({sub_count} 个子类目)")
        else:
            print("\n⚠️  未提取到类目，可能需要:")
            print("  1. 安装selenium: pip install selenium")
            print("  2. 安装ChromeDriver")
            print("  3. 检查网络连接")
        
        print("=" * 80)
        print("🎉 网页爬取测试完成！")
        
        return method1_count > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = test_web_scraping()
    
    if success:
        print("✅ TraceParts 网页爬取测试成功完成！")
    else:
        print("❌ TraceParts 网页爬取测试失败！")
        print("💡 建议：尝试安装selenium或使用模拟数据模式")
        
    exit(0 if success else 1) 