#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展分类树缓存 - 添加产品链接
==============================
将第二阶段爬取的产品链接合并到classification_tree.json中，
使叶节点包含products字段，形成完整的缓存文件
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到路径
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.crawler.ultimate_products import UltimateProductLinksCrawler
from src.utils.thread_safe_logger import ThreadSafeLogger, ProgressTracker


class CacheExtender:
    """扩展分类树缓存，添加产品链接"""
    
    def __init__(self, max_workers: int = 16):
        self.max_workers = max_workers
        self.logger = ThreadSafeLogger("cache-extender", logging.INFO)
        self.progress_tracker = ProgressTracker(self.logger)
        self.products_crawler = UltimateProductLinksCrawler()
        
        # 缓存路径
        self.cache_dir = Path('results/cache')
        self.cache_file = self.cache_dir / 'classification_tree.json'
        self.products_cache_dir = self.cache_dir / 'products'
        self.products_cache_dir.mkdir(parents=True, exist_ok=True)
        
    def load_classification_tree(self) -> Dict[str, Any]:
        """加载现有的分类树缓存"""
        if not self.cache_file.exists():
            self.logger.error(f"分类树缓存文件不存在: {self.cache_file}")
            raise FileNotFoundError(f"Classification tree cache not found: {self.cache_file}")
            
        self.logger.info(f"📂 加载分类树缓存: {self.cache_file}")
        with open(self.cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.logger.info(f"✅ 已加载分类树，包含 {len(data.get('leaves', []))} 个叶节点")
        return data
    
    def get_cached_products(self, leaf_code: str) -> List[str]:
        """获取叶节点的缓存产品链接"""
        cache_file = self.products_cache_dir / f"{leaf_code}.json"
        
        if cache_file.exists():
            # 检查缓存时效（24小时）
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < 86400:  # 24小时
                with open(cache_file, 'r', encoding='utf-8') as f:
                    products = json.load(f)
                return products
        
        return None
    
    def save_products_cache(self, leaf_code: str, products: List[str]):
        """保存产品链接到缓存"""
        cache_file = self.products_cache_dir / f"{leaf_code}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
    
    def crawl_products_for_leaf(self, leaf: Dict) -> List[str]:
        """为单个叶节点爬取产品链接（带缓存）"""
        code = leaf['code']
        
        # 先检查缓存
        cached_products = self.get_cached_products(code)
        if cached_products is not None:
            self.logger.info(f"📦 使用缓存: {code} ({len(cached_products)} 个产品)")
            return cached_products
        
        # 爬取新数据
        self.logger.info(f"🌐 爬取产品: {code} - {leaf['url']}")
        try:
            products = self.products_crawler.extract_product_links(leaf['url'])
            # 保存到缓存
            self.save_products_cache(code, products)
            self.logger.info(f"✅ 成功爬取 {code}: {len(products)} 个产品")
            return products
        except Exception as e:
            self.logger.error(f"❌ 爬取失败 {code}: {e}")
            return []
    
    def extend_tree_with_products(self, tree_data: Dict) -> Dict:
        """为树的所有叶节点添加产品链接"""
        root = tree_data['root']
        leaves = tree_data['leaves']
        
        self.logger.info(f"\n开始扩展分类树，为 {len(leaves)} 个叶节点添加产品链接...")
        
        # 注册进度跟踪
        self.progress_tracker.register_task("产品链接扩展", len(leaves))
        
        # 并行处理所有叶节点
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_leaf = {
                executor.submit(self.crawl_products_for_leaf, leaf): leaf 
                for leaf in leaves
            }
            
            # 收集结果
            leaf_products = {}
            for future in as_completed(future_to_leaf):
                leaf = future_to_leaf[future]
                try:
                    products = future.result()
                    leaf_products[leaf['code']] = products
                    self.progress_tracker.update_task("产品链接扩展", success=True)
                except Exception as e:
                    self.logger.error(f"处理叶节点 {leaf['code']} 失败: {e}")
                    leaf_products[leaf['code']] = []
                    self.progress_tracker.update_task("产品链接扩展", success=False)
        
        # 更新树结构，为每个叶节点添加products字段
        def update_node(node: Dict):
            """递归更新节点，为叶节点添加产品链接"""
            if node.get('is_leaf', False):
                code = node.get('code', '')
                node['products'] = leaf_products.get(code, [])
                node['product_count'] = len(node['products'])
            
            # 递归处理子节点
            for child in node.get('children', []):
                update_node(child)
        
        # 从根节点开始更新
        update_node(root)
        
        # 同时更新leaves列表
        for leaf in leaves:
            code = leaf['code']
            leaf['products'] = leaf_products.get(code, [])
            leaf['product_count'] = len(leaf['products'])
        
        # 统计信息
        total_products = sum(len(products) for products in leaf_products.values())
        self.logger.info(f"\n✅ 扩展完成:")
        self.logger.info(f"   • 处理叶节点: {len(leaves)} 个")
        self.logger.info(f"   • 总产品数: {total_products} 个")
        
        return tree_data
    
    def save_extended_cache(self, tree_data: Dict):
        """保存扩展后的缓存"""
        # 备份原文件
        if self.cache_file.exists():
            backup_file = self.cache_file.with_suffix('.json.bak')
            self.cache_file.rename(backup_file)
            self.logger.info(f"📋 已备份原文件到: {backup_file}")
        
        # 添加元数据
        tree_data['metadata'] = {
            'generated': datetime.now().isoformat(),
            'extended_at': datetime.now().isoformat(),
            'version': '2.0-with-products',
            'total_leaves': len(tree_data.get('leaves', [])),
            'total_products': sum(leaf.get('product_count', 0) for leaf in tree_data.get('leaves', []))
        }
        
        # 保存新文件
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(tree_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"💾 已保存扩展后的缓存到: {self.cache_file}")
        self.logger.info(f"   文件大小: {self.cache_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    def run(self):
        """运行扩展流程"""
        self.logger.info("\n" + "="*60)
        self.logger.info("🚀 分类树缓存扩展工具")
        self.logger.info("="*60)
        
        try:
            # 1. 加载现有分类树
            tree_data = self.load_classification_tree()
            
            # 2. 扩展树结构，添加产品链接
            extended_tree = self.extend_tree_with_products(tree_data)
            
            # 3. 保存扩展后的缓存
            self.save_extended_cache(extended_tree)
            
            self.logger.info("\n✅ 扩展完成！下次运行时将直接使用完整缓存。")
            
        except Exception as e:
            self.logger.error(f"扩展失败: {e}", exc_info=True)
            raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='扩展分类树缓存，添加产品链接')
    parser.add_argument('--workers', type=int, default=16, help='最大并发数 (默认: 16)')
    
    args = parser.parse_args()
    
    extender = CacheExtender(max_workers=args.workers)
    extender.run()


if __name__ == '__main__':
    main() 