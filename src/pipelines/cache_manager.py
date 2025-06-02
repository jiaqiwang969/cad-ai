#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一缓存管理器
=============
支持三阶段缓存：
1. 分类树（classification tree）
2. 产品链接（product links）
3. 产品规格（product specifications）

每个阶段可以独立更新，系统会自动识别缓存级别
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

# 添加项目根目录到路径
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.crawler.classification_optimized import OptimizedClassificationCrawler
from src.crawler.ultimate_products import UltimateProductLinksCrawler
from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
from src.utils.thread_safe_logger import ThreadSafeLogger, ProgressTracker


class CacheLevel(Enum):
    """缓存级别枚举"""
    NONE = 0
    CLASSIFICATION = 1  # 仅分类树
    PRODUCTS = 2       # 分类树 + 产品链接
    SPECIFICATIONS = 3  # 分类树 + 产品链接 + 产品规格


class CacheManager:
    """统一的缓存管理器"""
    
    def __init__(self, cache_dir: str = 'results/cache', max_workers: int = 16):
        self.cache_dir = Path(cache_dir)
        self.max_workers = max_workers
        self.logger = ThreadSafeLogger("cache-manager", logging.INFO)
        self.progress_tracker = ProgressTracker(self.logger)
        
        # 缓存文件路径
        self.main_cache_file = self.cache_dir / 'classification_tree_full.json'
        self.products_cache_dir = self.cache_dir / 'products'
        self.specs_cache_dir = self.cache_dir / 'specifications'
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.products_cache_dir.mkdir(parents=True, exist_ok=True)
        self.specs_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化爬取器
        self.classification_crawler = OptimizedClassificationCrawler()
        self.products_crawler = UltimateProductLinksCrawler()
        self.specifications_crawler = OptimizedSpecificationsCrawler()
        
        # 缓存有效期（小时）
        self.cache_ttl = {
            CacheLevel.CLASSIFICATION: 24 * 7,  # 分类树：7天
            CacheLevel.PRODUCTS: 24 * 3,       # 产品链接：3天
            CacheLevel.SPECIFICATIONS: 24      # 产品规格：1天
        }
    
    def get_cache_level(self) -> Tuple[CacheLevel, Optional[Dict]]:
        """获取当前缓存级别和缓存数据"""
        if not self.main_cache_file.exists():
            return CacheLevel.NONE, None
        
        try:
            with open(self.main_cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            cache_level = CacheLevel(metadata.get('cache_level', 0))
            
            # 检查缓存是否过期
            if 'generated' in metadata:
                generated_time = datetime.fromisoformat(metadata['generated'])
                age_hours = (datetime.now() - generated_time).total_seconds() / 3600
                
                if age_hours > self.cache_ttl.get(cache_level, 24):
                    self.logger.warning(f"缓存已过期 (年龄: {age_hours:.1f}小时)")
                    return CacheLevel.NONE, None
            
            return cache_level, data
            
        except Exception as e:
            self.logger.error(f"读取缓存失败: {e}")
            return CacheLevel.NONE, None
    
    def save_cache(self, data: Dict, level: CacheLevel):
        """保存缓存数据"""
        # 备份现有文件
        if self.main_cache_file.exists():
            backup_file = self.main_cache_file.with_suffix('.json.bak')
            self.main_cache_file.rename(backup_file)
            self.logger.info(f"📋 已备份原文件到: {backup_file}")
        
        # 计算规格总数（只有在SPECIFICATIONS级别才有规格数据）
        total_specifications = 0
        if level == CacheLevel.SPECIFICATIONS:
            for leaf in data.get('leaves', []):
                for product in leaf.get('products', []):
                    if isinstance(product, dict):
                        total_specifications += len(product.get('specifications', []))
        
        # 更新元数据
        data['metadata'] = {
            'generated': datetime.now().isoformat(),
            'cache_level': level.value,
            'cache_level_name': level.name,
            'version': f'3.0-{level.name.lower()}',
            'total_leaves': len(data.get('leaves', [])),
            'total_products': sum(leaf.get('product_count', 0) for leaf in data.get('leaves', [])),
            'total_specifications': total_specifications
        }
        
        # 保存文件
        with open(self.main_cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        file_size_mb = self.main_cache_file.stat().st_size / 1024 / 1024
        self.logger.info(f"💾 已保存缓存到: {self.main_cache_file}")
        self.logger.info(f"   缓存级别: {level.name}")
        self.logger.info(f"   文件大小: {file_size_mb:.1f} MB")
    
    def extend_to_products(self, data: Dict) -> Dict:
        """扩展缓存到产品链接级别"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📦 扩展缓存：添加产品链接")
        self.logger.info("="*60)
        
        leaves = data['leaves']
        self.progress_tracker.register_task("产品链接扩展", len(leaves))
        
        # 并行爬取产品链接
        leaf_products = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_leaf = {
                executor.submit(self._crawl_products_for_leaf, leaf): leaf
                for leaf in leaves
            }
            
            for future in as_completed(future_to_leaf):
                leaf = future_to_leaf[future]
                try:
                    products = future.result()
                    leaf_products[leaf['code']] = products
                    self.progress_tracker.update_task("产品链接扩展", success=True)
                    
                    # 显示成功信息（包含URL）
                    if products:
                        self.logger.info(f"✅ 叶节点 {leaf['code']} 产品数: {len(products)}")
                        self.logger.info(f"   地址: {leaf['url']}")
                    else:
                        self.logger.warning(f"⚠️  叶节点 {leaf['code']} 无产品")
                        self.logger.warning(f"   地址: {leaf['url']}")
                        
                except Exception as e:
                    self.logger.error(f"叶节点 {leaf['code']} 处理失败: {e}")
                    self.logger.error(f"   地址: {leaf['url']}")
                    leaf_products[leaf['code']] = []
                    self.progress_tracker.update_task("产品链接扩展", success=False)
        
        # 更新数据结构
        self._update_tree_with_products(data, leaf_products)
        
        # 统计
        total_products = sum(len(products) for products in leaf_products.values())
        self.logger.info(f"\n✅ 产品链接扩展完成:")
        self.logger.info(f"   • 处理叶节点: {len(leaves)} 个")
        self.logger.info(f"   • 总产品数: {total_products} 个")
        
        return data
    
    def extend_to_specifications(self, data: Dict) -> Dict:
        """扩展缓存到产品规格级别"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📋 扩展缓存：添加产品规格")
        self.logger.info("="*60)
        
        # 收集所有需要爬取规格的产品
        all_products = []
        for leaf in data['leaves']:
            leaf_code = leaf['code']
            for product_url in leaf.get('products', []):
                # 如果是字符串URL，转换为字典格式
                if isinstance(product_url, str):
                    product_info = {
                        'product_url': product_url,
                        'leaf_code': leaf_code
                    }
                else:
                    product_info = product_url
                    product_info['leaf_code'] = leaf_code
                all_products.append(product_info)
        
        self.logger.info(f"准备爬取 {len(all_products)} 个产品的规格...")
        self.progress_tracker.register_task("产品规格扩展", len(all_products))
        
        # 并行爬取产品规格
        product_specs = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_product = {
                executor.submit(self._crawl_specs_for_product, p): p
                for p in all_products
            }
            
            for future in as_completed(future_to_product):
                product = future_to_product[future]
                try:
                    specs = future.result()
                    product_url = product['product_url'] if isinstance(product, dict) else product
                    product_specs[product_url] = specs
                    self.progress_tracker.update_task("产品规格扩展", success=True)
                except Exception as e:
                    self.logger.error(f"产品规格爬取失败: {e}")
                    product_url = product['product_url'] if isinstance(product, dict) else product
                    product_specs[product_url] = []
                    self.progress_tracker.update_task("产品规格扩展", success=False)
        
        # 更新数据结构
        self._update_tree_with_specifications(data, product_specs)
        
        # 统计
        total_specs = sum(len(specs) for specs in product_specs.values())
        self.logger.info(f"\n✅ 产品规格扩展完成:")
        self.logger.info(f"   • 处理产品: {len(all_products)} 个")
        self.logger.info(f"   • 总规格数: {total_specs} 个")
        
        return data
    
    def _crawl_products_for_leaf(self, leaf: Dict) -> List[str]:
        """为叶节点爬取产品链接（带缓存）"""
        code = leaf['code']
        cache_file = self.products_cache_dir / f"{code}.json"
        
        # 检查缓存
        if cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < self.cache_ttl[CacheLevel.PRODUCTS] * 3600:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    products = json.load(f)
                self.logger.info(f"📦 使用缓存: {code} ({len(products)} 个产品)")
                return products
        
        # 爬取新数据
        self.logger.info(f"🌐 爬取产品: {code}")
        try:
            products = self.products_crawler.extract_product_links(leaf['url'])
            # 保存缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            return products
        except Exception as e:
            self.logger.error(f"❌ 失败: {code} - {e}")
            return []
    
    def _crawl_specs_for_product(self, product: Any) -> List[Dict]:
        """为产品爬取规格（带缓存）"""
        if isinstance(product, dict):
            product_url = product['product_url']
            leaf_code = product.get('leaf_code', 'unknown')
        else:
            product_url = product
            leaf_code = 'unknown'
        
        # 生成缓存文件名（使用URL的hash）
        import hashlib
        url_hash = hashlib.md5(product_url.encode()).hexdigest()[:12]
        cache_file = self.specs_cache_dir / f"{leaf_code}_{url_hash}.json"
        
        # 检查缓存
        if cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < self.cache_ttl[CacheLevel.SPECIFICATIONS] * 3600:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    specs = json.load(f)
                return specs
        
        # 爬取新数据
        try:
            result = self.specifications_crawler.extract_specifications(product_url)
            specs = result.get('specifications', [])
            # 保存缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(specs, f, ensure_ascii=False, indent=2)
            return specs
        except Exception as e:
            self.logger.error(f"规格爬取失败: {e}")
            return []
    
    def _update_tree_with_products(self, data: Dict, leaf_products: Dict[str, List[str]]):
        """更新树结构，添加产品链接"""
        def update_node(node: Dict):
            if node.get('is_leaf', False):
                code = node.get('code', '')
                products = leaf_products.get(code, [])
                node['products'] = products
                node['product_count'] = len(products)
            
            for child in node.get('children', []):
                update_node(child)
        
        # 更新树
        update_node(data['root'])
        
        # 更新叶节点列表
        for leaf in data['leaves']:
            code = leaf['code']
            products = leaf_products.get(code, [])
            leaf['products'] = products
            leaf['product_count'] = len(products)
    
    def _update_tree_with_specifications(self, data: Dict, product_specs: Dict[str, List[Dict]]):
        """更新树结构，添加产品规格"""
        def update_node(node: Dict):
            if node.get('is_leaf', False):
                # 更新产品列表格式
                updated_products = []
                for product in node.get('products', []):
                    if isinstance(product, str):
                        # 转换为字典格式
                        product_info = {
                            'product_url': product,
                            'specifications': product_specs.get(product, []),
                            'spec_count': len(product_specs.get(product, []))
                        }
                    else:
                        # 更新现有字典
                        product['specifications'] = product_specs.get(product['product_url'], [])
                        product['spec_count'] = len(product['specifications'])
                        product_info = product
                    updated_products.append(product_info)
                node['products'] = updated_products
            
            for child in node.get('children', []):
                update_node(child)
        
        # 更新树
        update_node(data['root'])
        
        # 更新叶节点列表
        for leaf in data['leaves']:
            updated_products = []
            for product in leaf.get('products', []):
                if isinstance(product, str):
                    product_info = {
                        'product_url': product,
                        'specifications': product_specs.get(product, []),
                        'spec_count': len(product_specs.get(product, []))
                    }
                else:
                    product['specifications'] = product_specs.get(product['product_url'], [])
                    product['spec_count'] = len(product['specifications'])
                    product_info = product
                updated_products.append(product_info)
            leaf['products'] = updated_products
    
    def run_progressive_cache(self, target_level: CacheLevel = CacheLevel.SPECIFICATIONS, force_refresh: bool = False):
        """运行渐进式缓存构建"""
        self.logger.info("\n" + "="*60)
        self.logger.info("🚀 TraceParts 渐进式缓存系统")
        self.logger.info("="*60)
        
        # 获取当前缓存级别
        current_level, data = self.get_cache_level()
        
        if force_refresh:
            self.logger.info("🔄 强制刷新模式，将重新构建所有缓存")
            current_level = CacheLevel.NONE
            data = None
        else:
            self.logger.info(f"📊 当前缓存级别: {current_level.name}")
            self.logger.info(f"🎯 目标缓存级别: {target_level.name}")
        
        # 逐级构建缓存
        if current_level.value < CacheLevel.CLASSIFICATION.value:
            self.logger.info("\n[阶段 1/3] 构建分类树缓存")
            self.logger.info("-" * 50)
            
            root, leaves = self.classification_crawler.crawl_full_tree()
            data = {'root': root, 'leaves': leaves}
            self.save_cache(data, CacheLevel.CLASSIFICATION)
            current_level = CacheLevel.CLASSIFICATION
            
            if target_level == CacheLevel.CLASSIFICATION:
                self.logger.info("\n✅ 已达到目标缓存级别")
                return data
        
        if current_level.value < CacheLevel.PRODUCTS.value and target_level.value >= CacheLevel.PRODUCTS.value:
            self.logger.info("\n[阶段 2/3] 扩展产品链接缓存")
            self.logger.info("-" * 50)
            
            data = self.extend_to_products(data)
            self.save_cache(data, CacheLevel.PRODUCTS)
            current_level = CacheLevel.PRODUCTS
            
            if target_level == CacheLevel.PRODUCTS:
                self.logger.info("\n✅ 已达到目标缓存级别")
                return data
        
        if current_level.value < CacheLevel.SPECIFICATIONS.value and target_level.value >= CacheLevel.SPECIFICATIONS.value:
            self.logger.info("\n[阶段 3/3] 扩展产品规格缓存")
            self.logger.info("-" * 50)
            
            data = self.extend_to_specifications(data)
            self.save_cache(data, CacheLevel.SPECIFICATIONS)
            
            self.logger.info("\n✅ 已达到目标缓存级别")
        
        return data 