#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量更新管理器
=============
智能差异检测系统，支持三级增量更新：
1. 新增分类树节点（新目录+叶节点）
2. 叶节点产品扩充（新产品链接）
3. 产品规格扩充（新产品规格）

核心原则：完全保留旧数据，只添加新增内容
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass

from src.pipelines.cache_manager import CacheManager, CacheLevel
from src.crawler.classification_optimized import OptimizedClassificationCrawler
from src.crawler.ultimate_products import UltimateProductLinksCrawler
from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
from src.utils.thread_safe_logger import ThreadSafeLogger


@dataclass
class UpdateStats:
    """更新统计信息"""
    new_leaves: int = 0
    updated_leaves: int = 0  # 有新产品的叶节点
    new_products: int = 0
    new_specifications: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def get_duration_minutes(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 60
        return 0.0


@dataclass 
class LeafComparison:
    """叶节点对比结果"""
    code: str
    name: str
    url: str
    old_product_count: int
    new_product_count: int
    is_new_leaf: bool
    has_new_products: bool
    new_product_urls: List[str]


class IncrementalUpdateManager:
    """增量更新管理器"""
    
    def __init__(self, cache_dir: str = 'results/cache', max_workers: int = 16):
        self.cache_dir = Path(cache_dir)
        self.max_workers = max_workers
        self.logger = ThreadSafeLogger("incremental-update", logging.INFO)
        
        # 使用现有的缓存管理器
        self.cache_manager = CacheManager(cache_dir=str(cache_dir), max_workers=max_workers)
        
        # 独立的爬取器（用于差异检测）
        self.classification_crawler = OptimizedClassificationCrawler()
        self.products_crawler = UltimateProductLinksCrawler()
        self.specifications_crawler = OptimizedSpecificationsCrawler(log_level=logging.INFO)
        
        # 统计信息
        self.stats = UpdateStats()
        
        # 备份目录
        self.backup_dir = self.cache_dir / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def run_incremental_update(self, target_level: CacheLevel = CacheLevel.SPECIFICATIONS) -> Dict:
        """
        运行增量更新
        
        Args:
            target_level: 目标更新级别
            
        Returns:
            更新后的完整数据
        """
        self.stats.start_time = datetime.now()
        
        self.logger.info("\n" + "="*70)
        self.logger.info("🔄 TraceParts 智能增量更新系统")
        self.logger.info("="*70)
        
        # 检查当前缓存状态
        current_level, current_data = self.cache_manager.get_cache_level()
        
        if current_level == CacheLevel.NONE:
            self.logger.warning("⚠️  未发现现有缓存，将执行全量构建")
            return self.cache_manager.run_progressive_cache(target_level=target_level)
        
        self.logger.info(f"📊 当前缓存级别: {current_level.name}")
        self.logger.info(f"🎯 目标更新级别: {target_level.name}")
        
        # 创建备份
        self._create_backup(current_data, current_level)
        
        # 执行增量更新
        updated_data = current_data.copy()
        
        try:
            # 阶段1：检测和更新分类树
            if target_level.value >= CacheLevel.CLASSIFICATION.value:
                updated_data = self._update_classification_tree(updated_data)
            
            # 阶段2：检测和更新产品链接
            if target_level.value >= CacheLevel.PRODUCTS.value:
                updated_data = self._update_product_links(updated_data)
            
            # 阶段3：检测和更新产品规格
            if target_level.value >= CacheLevel.SPECIFICATIONS.value:
                updated_data = self._update_specifications(updated_data)
            
            # 保存更新后的缓存
            self.cache_manager.save_cache(updated_data, target_level)
            
            # 打印更新汇总
            self._print_update_summary()
            
            return updated_data
            
        except Exception as e:
            self.logger.error(f"❌ 增量更新失败: {e}", exc_info=True)
            self.logger.info("🔄 可使用备份文件恢复")
            raise
    
    def _create_backup(self, data: Dict, level: CacheLevel):
        """创建数据备份"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f'backup_{level.name.lower()}_v{timestamp}.json'
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"💾 已创建数据备份: {backup_file.name}")
    
    def _update_classification_tree(self, current_data: Dict) -> Dict:
        """更新分类树 - 检测新增叶节点"""
        self.logger.info("\n" + "🌳 [阶段 1/3] 检测分类树变化")
        self.logger.info("-" * 60)
        
        # 获取最新的分类树
        self.logger.info("🌐 爬取最新分类树结构...")
        new_root, new_leaves = self.classification_crawler.crawl_full_tree()
        
        # 对比叶节点
        old_leaf_codes = {leaf['code'] for leaf in current_data['leaves']}
        new_leaf_codes = {leaf['code'] for leaf in new_leaves}
        
        added_leaf_codes = new_leaf_codes - old_leaf_codes
        self.stats.new_leaves = len(added_leaf_codes)
        
        if added_leaf_codes:
            self.logger.info(f"🆕 发现新增叶节点: {len(added_leaf_codes)} 个")
            for code in sorted(added_leaf_codes):
                new_leaf = next(leaf for leaf in new_leaves if leaf['code'] == code)
                self.logger.info(f"   • {code}: {new_leaf.get('name', '')}")
                self.logger.info(f"     URL: {new_leaf['url']}")
            
            # 合并新叶节点到现有数据
            updated_data = self._merge_new_leaves(current_data, new_leaves, added_leaf_codes)
            self.logger.info(f"✅ 已合并 {len(added_leaf_codes)} 个新叶节点")
            
        else:
            self.logger.info("✅ 分类树无变化，跳过此阶段")
            updated_data = current_data
        
        return updated_data
    
    def _merge_new_leaves(self, current_data: Dict, new_leaves: List[Dict], new_leaf_codes: Set[str]) -> Dict:
        """合并新增叶节点到现有数据"""
        updated_data = current_data.copy()
        
        # 添加新叶节点到叶节点列表
        new_leaves_to_add = [leaf for leaf in new_leaves if leaf['code'] in new_leaf_codes]
        updated_data['leaves'].extend(new_leaves_to_add)
        
        # 更新分类树结构（这里简化处理，实际可能需要更复杂的树合并逻辑）
        # 由于新的分类树包含了完整结构，我们使用新的根节点
        # 但保留现有叶节点的产品数据
        self.logger.info("🔄 正在更新分类树结构...")
        
        # 这里需要智能合并树结构，保留现有数据
        # 暂时使用简单策略：使用新的树结构，但会在后续步骤中保留产品数据
        updated_data['root'] = self._crawl_new_tree_with_preserved_data(current_data)
        
        return updated_data
    
    def _crawl_new_tree_with_preserved_data(self, current_data: Dict) -> Dict:
        """爬取新的树结构，但保留现有的产品数据"""
        # 获取最新的完整树结构
        new_root, _ = self.classification_crawler.crawl_full_tree()
        
        # 创建现有数据的映射
        existing_leaf_data = {
            leaf['code']: leaf for leaf in current_data['leaves']
        }
        
        # 递归更新树节点，保留现有的产品数据
        def preserve_existing_data(node: Dict):
            if node.get('is_leaf', False):
                code = node.get('code', '')
                if code in existing_leaf_data:
                    # 保留现有的产品数据
                    existing_leaf = existing_leaf_data[code]
                    node['products'] = existing_leaf.get('products', [])
                    node['product_count'] = existing_leaf.get('product_count', 0)
            
            # 递归处理子节点
            for child in node.get('children', []):
                preserve_existing_data(child)
        
        preserve_existing_data(new_root)
        return new_root
    
    def _update_product_links(self, current_data: Dict) -> Dict:
        """更新产品链接 - 检测新增产品"""
        self.logger.info("\n" + "📦 [阶段 2/3] 检测产品链接变化")
        self.logger.info("-" * 60)
        
        # 对比每个叶节点的产品数量
        leaf_comparisons = self._compare_leaf_products(current_data['leaves'])
        
        # 统计需要更新的叶节点
        leaves_to_update = [comp for comp in leaf_comparisons if comp.is_new_leaf or comp.has_new_products]
        
        if not leaves_to_update:
            self.logger.info("✅ 所有叶节点产品无变化，跳过此阶段")
            return current_data
        
        self.logger.info(f"📊 产品链接变化统计:")
        self.logger.info(f"   • 新增叶节点: {sum(1 for c in leaf_comparisons if c.is_new_leaf)} 个")
        self.logger.info(f"   • 有新产品的叶节点: {sum(1 for c in leaf_comparisons if c.has_new_products and not c.is_new_leaf)} 个")
        
        # 更新有变化的叶节点
        updated_data = self._update_changed_leaves(current_data, leaves_to_update)
        
        return updated_data
    
    def _compare_leaf_products(self, current_leaves: List[Dict]) -> List[LeafComparison]:
        """对比叶节点的产品数量变化"""
        comparisons = []
        
        for leaf in current_leaves:
            self.logger.info(f"🔍 检查叶节点: {leaf['code']}")
            
            try:
                # 获取当前产品链接数量
                current_product_urls = leaf.get('products', [])
                if isinstance(current_product_urls, list) and current_product_urls:
                    if isinstance(current_product_urls[0], dict):
                        # 新格式：包含规格的字典
                        current_urls = [p['product_url'] for p in current_product_urls]
                    else:
                        # 旧格式：直接的URL列表
                        current_urls = current_product_urls
                else:
                    current_urls = []
                
                old_count = len(current_urls)
                
                # 爬取最新的产品链接
                latest_urls = self.products_crawler.extract_product_links(leaf['url'])
                new_count = len(latest_urls)
                
                # 检测新增产品
                current_url_set = set(current_urls)
                latest_url_set = set(latest_urls)
                new_product_urls = list(latest_url_set - current_url_set)
                
                is_new_leaf = old_count == 0  # 如果原来没有产品，认为是新叶节点
                has_new_products = len(new_product_urls) > 0
                
                comparison = LeafComparison(
                    code=leaf['code'],
                    name=leaf.get('name', ''),
                    url=leaf['url'],
                    old_product_count=old_count,
                    new_product_count=new_count,
                    is_new_leaf=is_new_leaf,
                    has_new_products=has_new_products,
                    new_product_urls=new_product_urls
                )
                
                if has_new_products or is_new_leaf:
                    self.logger.info(f"   📈 {leaf['code']}: {old_count} → {new_count} (+{len(new_product_urls)})")
                else:
                    self.logger.info(f"   ✅ {leaf['code']}: {old_count} (无变化)")
                
                comparisons.append(comparison)
                
            except Exception as e:
                self.logger.error(f"   ❌ {leaf['code']}: 检查失败 - {e}")
                # 创建一个失败的对比结果
                comparison = LeafComparison(
                    code=leaf['code'],
                    name=leaf.get('name', ''),
                    url=leaf['url'],
                    old_product_count=len(leaf.get('products', [])),
                    new_product_count=0,
                    is_new_leaf=False,
                    has_new_products=False,
                    new_product_urls=[]
                )
                comparisons.append(comparison)
        
        return comparisons
    
    def _update_changed_leaves(self, current_data: Dict, leaves_to_update: List[LeafComparison]) -> Dict:
        """更新有变化的叶节点"""
        updated_data = current_data.copy()
        
        for comparison in leaves_to_update:
            try:
                self.logger.info(f"🔄 更新叶节点: {comparison.code}")
                
                if comparison.is_new_leaf:
                    # 新叶节点：爬取所有产品
                    new_urls = self.products_crawler.extract_product_links(comparison.url)
                    self.logger.info(f"   🆕 新叶节点，爬取到 {len(new_urls)} 个产品")
                    self.stats.new_products += len(new_urls)
                else:
                    # 现有叶节点：只添加新产品
                    new_urls = comparison.new_product_urls
                    self.logger.info(f"   📈 新增 {len(new_urls)} 个产品")
                    self.stats.new_products += len(new_urls)
                
                # 更新叶节点数据
                self._merge_new_products_to_leaf(updated_data, comparison, new_urls)
                self.stats.updated_leaves += 1
                
            except Exception as e:
                self.logger.error(f"❌ 更新叶节点 {comparison.code} 失败: {e}")
        
        return updated_data
    
    def _merge_new_products_to_leaf(self, data: Dict, comparison: LeafComparison, new_urls: List[str]):
        """将新产品合并到叶节点"""
        # 更新叶节点列表中的数据
        for leaf in data['leaves']:
            if leaf['code'] == comparison.code:
                existing_products = leaf.get('products', [])
                
                if comparison.is_new_leaf:
                    # 新叶节点：直接设置产品列表
                    leaf['products'] = new_urls
                    leaf['product_count'] = len(new_urls)
                else:
                    # 现有叶节点：合并新产品
                    if isinstance(existing_products, list) and existing_products:
                        if isinstance(existing_products[0], dict):
                            # 新格式：保持字典格式
                            existing_urls = {p['product_url'] for p in existing_products}
                            for url in new_urls:
                                if url not in existing_urls:
                                    existing_products.append({'product_url': url})
                        else:
                            # 旧格式：URL列表
                            existing_url_set = set(existing_products)
                            for url in new_urls:
                                if url not in existing_url_set:
                                    existing_products.append(url)
                    else:
                        # 空列表或None
                        leaf['products'] = new_urls
                    
                    leaf['product_count'] = len(leaf['products'])
                break
        
        # 同时更新树结构中的数据
        def update_tree_node(node: Dict):
            if node.get('is_leaf', False) and node.get('code') == comparison.code:
                # 与叶节点列表保持同步
                leaf_data = next(leaf for leaf in data['leaves'] if leaf['code'] == comparison.code)
                node['products'] = leaf_data['products']
                node['product_count'] = leaf_data['product_count']
            
            for child in node.get('children', []):
                update_tree_node(child)
        
        update_tree_node(data['root'])
    
    def _update_specifications(self, current_data: Dict) -> Dict:
        """更新产品规格 - 检测新增产品规格"""
        self.logger.info("\n" + "📋 [阶段 3/3] 检测产品规格变化")
        self.logger.info("-" * 60)
        
        # 收集所有需要爬取规格的新产品
        products_needing_specs = self._identify_products_needing_specs(current_data)
        
        if not products_needing_specs:
            self.logger.info("✅ 无新产品需要爬取规格，跳过此阶段")
            return current_data
        
        self.logger.info(f"📊 需要爬取规格的产品: {len(products_needing_specs)} 个")
        
        # 批量爬取新产品规格
        updated_data = self._crawl_specifications_for_new_products(current_data, products_needing_specs)
        
        return updated_data
    
    def _identify_products_needing_specs(self, current_data: Dict) -> List[Dict]:
        """识别需要爬取规格的产品"""
        products_needing_specs = []
        
        for leaf in current_data['leaves']:
            for product in leaf.get('products', []):
                if isinstance(product, str):
                    # 旧格式的URL，需要爬取规格
                    products_needing_specs.append({
                        'product_url': product,
                        'leaf_code': leaf['code'],
                        'is_new': True
                    })
                elif isinstance(product, dict):
                    if 'specifications' not in product or not product.get('specifications'):
                        # 字典格式但没有规格数据
                        products_needing_specs.append({
                            'product_url': product['product_url'],
                            'leaf_code': leaf['code'],
                            'is_new': True
                        })
        
        return products_needing_specs
    
    def _crawl_specifications_for_new_products(self, current_data: Dict, products_needing_specs: List[Dict]) -> Dict:
        """为新产品爬取规格"""
        # 提取URL列表
        product_urls = [p['product_url'] for p in products_needing_specs]
        
        # 批量爬取规格
        self.logger.info(f"🌐 开始批量爬取 {len(product_urls)} 个产品的规格...")
        batch_result = self.specifications_crawler.extract_batch_specifications(
            product_urls, 
            max_workers=min(len(product_urls), 12)
        )
        
        # 处理结果
        product_specs = {}
        success_count = 0
        
        for result in batch_result.get('results', []):
            product_url = result['product_url']
            specs = result.get('specifications', [])
            product_specs[product_url] = specs
            
            if result.get('success', False):
                success_count += 1
                self.stats.new_specifications += len(specs)
        
        self.logger.info(f"✅ 规格爬取完成: {success_count}/{len(product_urls)} 成功")
        self.logger.info(f"📊 新增规格总数: {self.stats.new_specifications}")
        
        # 更新数据结构
        updated_data = self._merge_specifications_to_data(current_data, product_specs)
        
        return updated_data
    
    def _merge_specifications_to_data(self, current_data: Dict, product_specs: Dict[str, List[Dict]]) -> Dict:
        """将规格数据合并到现有数据"""
        updated_data = current_data.copy()
        
        # 更新叶节点中的产品格式
        for leaf in updated_data['leaves']:
            updated_products = []
            for product in leaf.get('products', []):
                if isinstance(product, str):
                    # 转换为字典格式并添加规格
                    product_info = {
                        'product_url': product,
                        'specifications': product_specs.get(product, []),
                        'spec_count': len(product_specs.get(product, []))
                    }
                else:
                    # 更新现有字典
                    if 'specifications' not in product or not product.get('specifications'):
                        product['specifications'] = product_specs.get(product['product_url'], [])
                        product['spec_count'] = len(product['specifications'])
                    product_info = product
                
                updated_products.append(product_info)
            
            leaf['products'] = updated_products
        
        # 同步更新树结构
        def update_tree_node(node: Dict):
            if node.get('is_leaf', False):
                # 找到对应的叶节点数据
                leaf_data = next((leaf for leaf in updated_data['leaves'] if leaf['code'] == node.get('code')), None)
                if leaf_data:
                    node['products'] = leaf_data['products']
                    node['product_count'] = leaf_data.get('product_count', 0)
            
            for child in node.get('children', []):
                update_tree_node(child)
        
        update_tree_node(updated_data['root'])
        
        return updated_data
    
    def _print_update_summary(self):
        """打印更新汇总"""
        self.stats.end_time = datetime.now()
        duration = self.stats.get_duration_minutes()
        
        self.logger.info("\n" + "="*70)
        self.logger.info("📊 增量更新完成 - 汇总报告")
        self.logger.info("="*70)
        
        self.logger.info(f"⏱️  总耗时: {duration:.1f} 分钟")
        self.logger.info(f"\n📈 更新统计:")
        self.logger.info(f"   • 新增叶节点: {self.stats.new_leaves} 个")
        self.logger.info(f"   • 更新叶节点: {self.stats.updated_leaves} 个")
        self.logger.info(f"   • 新增产品: {self.stats.new_products} 个")
        self.logger.info(f"   • 新增规格: {self.stats.new_specifications} 个")
        
        self.logger.info(f"\n💾 数据保存:")
        self.logger.info(f"   • 缓存目录: {self.cache_dir}")
        self.logger.info(f"   • 备份目录: {self.backup_dir}")
        
        self.logger.info("="*70) 