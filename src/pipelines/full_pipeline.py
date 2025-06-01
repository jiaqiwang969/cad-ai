#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整流水线模块
=============
整合分类树、产品链接、产品规格的完整爬取流程
"""

import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from config.settings import Settings
from config.logging_config import get_logger
from src.utils.browser_manager import create_browser_manager
from src.utils.net_guard import get_network_stats
from src.crawler.classification import ClassificationCrawler
from src.crawler.products import ProductLinksCrawler
from src.crawler.specifications import SpecificationsCrawler


logger = get_logger(__name__)


class FullPipeline:
    """完整爬取流水线"""
    
    def __init__(self, max_workers: int = None, browser_type: str = None):
        """
        初始化流水线
        
        Args:
            max_workers: 最大并发数
            browser_type: 浏览器类型
        """
        self.max_workers = max_workers or Settings.CRAWLER['max_workers']
        # 创建共享的浏览器管理器，池大小与并发数匹配
        self.browser_manager = create_browser_manager(browser_type, pool_size=self.max_workers)
        
        # 初始化各个爬取器，使用共享的浏览器管理器
        self.classification_crawler = ClassificationCrawler(self.browser_manager)
        self.products_crawler = ProductLinksCrawler(self.browser_manager)
        self.specifications_crawler = SpecificationsCrawler(self.browser_manager)
        
        # 统计信息
        self.stats = {
            'start_time': None,
            'end_time': None,
            'duration': None,
            'total_leaves': 0,
            'total_products': 0,
            'total_specifications': 0,
            'success_leaves': 0,
            'success_products': 0,
            'failed_leaves': [],
            'failed_products': []
        }
    
    def run(self, output_file: str = None, cache_enabled: bool = True) -> Dict[str, Any]:
        """
        运行完整流水线
        
        Args:
            output_file: 输出文件路径
            cache_enabled: 是否启用缓存
            
        Returns:
            爬取结果
        """
        self.stats['start_time'] = datetime.now()
        logger.info("🚀 开始运行完整爬取流水线")
        
        try:
            # 1. 爬取分类树
            logger.info("=" * 60)
            logger.info("📋 第一步：爬取分类树")
            logger.info("=" * 60)
            
            root, leaves = self._crawl_classification_tree(cache_enabled)
            if not root or not leaves:
                logger.error("分类树爬取失败，终止流水线")
                return None
            
            self.stats['total_leaves'] = len(leaves)
            
            # 2. 爬取产品链接
            logger.info("=" * 60)
            logger.info("📦 第二步：爬取产品链接")
            logger.info("=" * 60)
            
            leaf_products = self._crawl_product_links(leaves)
            
            # 3. 爬取产品规格
            logger.info("=" * 60)
            logger.info("📊 第三步：爬取产品规格")
            logger.info("=" * 60)
            
            final_data = self._crawl_specifications(leaves, leaf_products)
            
            # 4. 保存结果
            result = self._save_results(root, final_data, output_file)
            
            # 统计
            self._calculate_stats()
            self._print_summary()
            
            return result
            
        except Exception as e:
            logger.error(f"流水线执行失败: {e}", exc_info=True)
            raise
        finally:
            # 清理资源
            self.browser_manager.shutdown()
    
    def _crawl_classification_tree(self, use_cache: bool) -> tuple:
        """爬取分类树"""
        cache_file = Path(Settings.STORAGE['cache_dir']) / 'classification_tree.json'
        
        # 检查缓存
        if use_cache and cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < Settings.STORAGE['cache_ttl']:
                logger.info(f"使用缓存的分类树 (年龄: {cache_age/3600:.1f}小时)")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data['root'], data['leaves']
        
        # 爬取新数据
        root, leaves = self.classification_crawler.crawl_full_tree()
        
        # 保存缓存
        if use_cache and root:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'root': root, 'leaves': leaves}, f, ensure_ascii=False, indent=2)
        
        return root, leaves
    
    def _crawl_product_links(self, leaves: List[Dict]) -> Dict[str, List[str]]:
        """批量爬取产品链接"""
        # 可以按批次处理，避免一次性处理太多
        batch_size = 50
        all_results = {}
        
        for i in range(0, len(leaves), batch_size):
            batch = leaves[i:i+batch_size]
            logger.info(f"处理叶节点批次 {i//batch_size + 1}/{(len(leaves)-1)//batch_size + 1}")
            
            batch_results = self.products_crawler.extract_batch_product_links(
                batch, 
                self.max_workers
            )
            all_results.update(batch_results)
            
            # 打印进度
            total_so_far = sum(len(links) for links in all_results.values())
            logger.info(f"当前累计产品链接数: {total_so_far}")
        
        return all_results
    
    def _crawl_specifications(self, 
                            leaves: List[Dict], 
                            leaf_products: Dict[str, List[str]]) -> List[Dict]:
        """批量爬取产品规格"""
        final_leaves = []
        
        for leaf in leaves:
            code = leaf['code']
            product_urls = leaf_products.get(code, [])
            
            leaf_info = {
                'name': leaf['name'],
                'code': code,
                'url': leaf['url'],
                'level': leaf['level'],
                'products': []
            }
            
            if product_urls:
                logger.info(f"处理叶节点 {code} 的 {len(product_urls)} 个产品")
                
                # 批量提取规格
                spec_results = self.specifications_crawler.extract_batch_specifications(
                    product_urls,
                    self.max_workers
                )
                
                # 整理数据
                for spec_result in spec_results:
                    product_info = {
                        'product_url': spec_result['product_url'],
                        'specifications': spec_result['specifications'],
                        'success': spec_result['success']
                    }
                    if not spec_result['success']:
                        product_info['error'] = spec_result.get('error', 'unknown')
                        self.stats['failed_products'].append(spec_result['product_url'])
                    
                    leaf_info['products'].append(product_info)
                
                self.stats['success_leaves'] += 1
            else:
                logger.warning(f"叶节点 {code} 没有产品")
                self.stats['failed_leaves'].append(code)
            
            final_leaves.append(leaf_info)
            
            # 统计规格数
            self.stats['total_specifications'] += sum(
                len(p['specifications']) for p in leaf_info['products']
            )
        
        return final_leaves
    
    def _save_results(self, root: Dict, leaves: List[Dict], output_file: str = None) -> Dict:
        """保存结果"""
        if not output_file:
            timestamp = int(time.time())
            output_file = Settings.STORAGE['products_dir'] + f'/full_pipeline_{timestamp}.json'
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = {
            'metadata': {
                'generated': datetime.now().isoformat(),
                'version': '2.0',
                'stats': self.stats
            },
            'root': root,
            'leaves': leaves
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 结果已保存到: {output_path.resolve()}")
        return result
    
    def _calculate_stats(self):
        """计算统计信息"""
        self.stats['end_time'] = datetime.now()
        self.stats['duration'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        # 计算产品总数
        self.stats['total_products'] = len(set(
            url for failed_list in self.stats['failed_products'] 
            for url in (failed_list if isinstance(failed_list, list) else [failed_list])
        )) + self.stats['success_products']
        
        # 获取网络统计
        self.stats['network'] = get_network_stats()
    
    def _print_summary(self):
        """打印汇总信息"""
        logger.info("=" * 60)
        logger.info("📊 爬取汇总")
        logger.info("=" * 60)
        
        duration_min = self.stats['duration'] / 60
        logger.info(f"⏱️  总耗时: {duration_min:.1f} 分钟")
        logger.info(f"🌳 叶节点: {self.stats['total_leaves']} 个")
        logger.info(f"📦 产品数: {self.stats['total_products']} 个")
        logger.info(f"📋 规格数: {self.stats['total_specifications']} 个")
        logger.info(f"✅ 成功率: {self.stats['success_leaves']}/{self.stats['total_leaves']} 叶节点")
        
        if self.stats['network']:
            logger.info(f"🌐 网络统计:")
            logger.info(f"   - 成功请求: {self.stats['network']['total_successes']}")
            logger.info(f"   - 失败请求: {self.stats['network']['total_failures']}")
            logger.info(f"   - 成功率: {self.stats['network']['success_rate']:.1%}")
            logger.info(f"   - 暂停次数: {self.stats['network']['total_pauses']}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TraceParts 完整爬取流水线')
    parser.add_argument('--workers', type=int, default=None, help='最大并发数')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径')
    parser.add_argument('--no-cache', action='store_true', help='禁用缓存')
    parser.add_argument('--browser', choices=['selenium', 'playwright'], 
                       default='selenium', help='浏览器类型')
    
    args = parser.parse_args()
    
    # 运行流水线
    pipeline = FullPipeline(
        max_workers=args.workers,
        browser_type=args.browser
    )
    
    pipeline.run(
        output_file=args.output,
        cache_enabled=not args.no_cache
    )


if __name__ == '__main__':
    main() 