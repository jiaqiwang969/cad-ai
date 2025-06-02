#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版完整流水线模块
==================
应用所有性能优化经验的完整爬取流程
"""

import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 导入优化版爬取器
from src.crawler.classification_optimized import OptimizedClassificationCrawler
from src.crawler.ultimate_products import UltimateProductLinksCrawler
from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
from src.utils.thread_safe_logger import ThreadSafeLogger, ProgressTracker


class OptimizedFullPipeline:
    """优化版完整爬取流水线"""
    
    # 预编译配置常量
    DEFAULT_MAX_WORKERS = 32
    BATCH_SIZE = 50
    CACHE_TTL = 86400  # 24小时
    
    def __init__(self, max_workers: int = None):
        """
        初始化优化版流水线
        
        Args:
            max_workers: 最大并发数
        """
        self.max_workers = max_workers or self.DEFAULT_MAX_WORKERS
        
        # 使用线程安全日志器
        self.logger = ThreadSafeLogger("opt-pipeline", logging.INFO)
        self.progress_tracker = ProgressTracker(self.logger)
        
        # 初始化优化版爬取器 (不使用浏览器池)
        self.classification_crawler = OptimizedClassificationCrawler()
        self.products_crawler = UltimateProductLinksCrawler()
        self.specifications_crawler = OptimizedSpecificationsCrawler()
        
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
        运行优化版完整流水线
        
        Args:
            output_file: 输出文件路径
            cache_enabled: 是否启用缓存
            
        Returns:
            爬取结果
        """
        self.stats['start_time'] = datetime.now()
        self.logger.info("\n" + "="*60)
        self.logger.info("🚀 TraceParts 产品数据爬取系统 v3.0")
        self.logger.info("="*60)
        self.logger.info("📋 爬取流程：")
        self.logger.info("   1. 爬取产品分类树 → 获取所有叶节点")
        self.logger.info("   2. 提取产品链接 → 从每个叶节点获取产品URL")
        self.logger.info("   3. 获取产品规格 → 爬取每个产品的详细参数")
        self.logger.info("")
        self.logger.info(f"⚙️  运行配置:")
        self.logger.info(f"   • 并发数: {self.max_workers} 个线程")
        self.logger.info(f"   • 缓存状态: {'✅ 启用' if cache_enabled else '❌ 禁用'}")
        if cache_enabled:
            self.logger.info(f"   • 缓存时效: 24 小时")
        self.logger.info("="*60)
        
        try:
            # 1. 爬取分类树
            self.logger.info("\n[步骤 1/3] 爬取产品分类树")
            self.logger.info("-" * 50)
            
            root, leaves = self._crawl_classification_tree(cache_enabled)
            if not root or not leaves:
                self.logger.error("❌ 分类树爬取失败，终止流水线")
                return None
            
            self.stats['total_leaves'] = len(leaves)
            self.logger.info(f"✅ 分类树爬取完成: 共发现 {len(leaves)} 个叶节点")
            
            # 2. 爬取产品链接
            self.logger.info("\n[步骤 2/3] 从叶节点提取产品链接")
            self.logger.info("-" * 50)
            self.logger.info(f"准备从 {len(leaves)} 个叶节点并行提取产品链接...")
            
            leaf_products = self._crawl_product_links_parallel(leaves)
            
            # 3. 爬取产品规格
            self.logger.info("\n[步骤 3/3] 爬取产品详细规格")
            self.logger.info("-" * 50)
            self.logger.info(f"准备爬取 {self.stats['total_products']} 个产品的详细规格参数...")
            
            final_data = self._crawl_specifications_parallel(leaves, leaf_products)
            
            # 4. 保存结果
            result = self._save_results(root, final_data, output_file)
            
            # 统计
            self._calculate_stats()
            self._print_summary()
            
            return result
            
        except Exception as e:
            self.logger.error(f"流水线执行失败: {e}", exc_info=True)
            raise
    
    def _crawl_classification_tree(self, use_cache: bool) -> tuple:
        """爬取分类树 (优化版)"""
        # 简化的缓存路径
        cache_file = Path('results/cache/classification_tree.json')
        
        # 检查缓存
        if use_cache and cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < self.CACHE_TTL:
                self.logger.info(f"📂 使用缓存的分类树")
                self.logger.info(f"   缓存文件: {cache_file.resolve()}")
                self.logger.info(f"   缓存年龄: {cache_age/3600:.1f} 小时")
                
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查是否是扩展版本（包含产品链接）
                metadata = data.get('metadata', {})
                version = metadata.get('version', '1.0')
                
                if 'with-products' in version:
                    self.logger.info(f"   ✨ 缓存版本: {version} (包含产品链接)")
                    self.logger.info(f"   产品总数: {metadata.get('total_products', 0)} 个")
                    self._has_cached_products = True
                else:
                    self.logger.info(f"   缓存版本: {version} (仅分类树)")
                    self._has_cached_products = False
                
                self.logger.info(f"   💡 提示: 使用 --no-cache 参数强制重新爬取")
                return data['root'], data['leaves']
            else:
                self.logger.info(f"⚠️  缓存已过期 (年龄: {cache_age/3600:.1f} 小时 > 24小时)")
                self.logger.info(f"   将重新爬取分类树...")
        
        # 爬取新数据
        self._has_cached_products = False
        if not use_cache:
            self.logger.info(f"🔄 强制重新爬取分类树 (--no-cache 参数)")
        elif not cache_file.exists():
            self.logger.info(f"📂 缓存文件不存在，将创建新缓存")
            self.logger.info(f"   缓存路径: {cache_file.resolve()}")
        
        self.logger.info(f"🌐 开始爬取分类树...")
        root, leaves = self.classification_crawler.crawl_full_tree()
        
        # 保存缓存
        if use_cache and root:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'root': root, 'leaves': leaves}, f, ensure_ascii=False, indent=2)
            self.logger.info(f"💾 分类树已缓存到: {cache_file.resolve()}")
        
        return root, leaves
    
    def _crawl_product_links_parallel(self, leaves: List[Dict]) -> Dict[str, List[str]]:
        """并行爬取产品链接 (优化版)"""
        all_results = {}
        
        # 如果缓存中已包含产品链接，直接使用
        if hasattr(self, '_has_cached_products') and self._has_cached_products:
            self.logger.info(f"📦 使用缓存的产品链接数据")
            
            # 从叶节点提取产品链接
            for leaf in leaves:
                products = leaf.get('products', [])
                all_results[leaf['code']] = products
                
                if products:
                    self.stats['success_leaves'] += 1
                    self.stats['total_products'] += len(products)
                else:
                    self.stats['failed_leaves'].append(leaf['code'])
            
            # 显示统计
            self.logger.info(f"✅ 从缓存加载完成:")
            self.logger.info(f"   • 成功叶节点: {self.stats['success_leaves']}/{len(leaves)}")
            self.logger.info(f"   • 空叶节点: {len(self.stats['failed_leaves'])}")
            self.logger.info(f"   • 总产品数: {self.stats['total_products']} 个")
            self.logger.info(f"   💡 提示: 使用 --no-cache 参数强制重新爬取")
            
            return all_results
        
        # 注册任务
        self.progress_tracker.register_task("产品链接提取", len(leaves))
        
        # 使用线程池并行处理
        self.logger.info(f"启动 {self.max_workers} 个并发线程...")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            self.logger.info("正在提交任务到线程池...")
            future_to_leaf = {
                executor.submit(
                    self.products_crawler.extract_product_links, 
                    leaf['url']
                ): leaf 
                for leaf in leaves
            }
            self.logger.info(f"已提交 {len(future_to_leaf)} 个任务，开始并行处理...")
            
            # 收集结果
            completed = 0
            for future in as_completed(future_to_leaf):
                leaf = future_to_leaf[future]
                completed += 1
                
                try:
                    links = future.result()
                    all_results[leaf['code']] = links
                    
                    if links:
                        self.stats['success_leaves'] += 1
                        self.stats['total_products'] += len(links)
                        self.progress_tracker.update_task("产品链接提取", success=True)
                        # 显示具体的叶节点信息和产品数
                        self.logger.info(f"✅ 叶节点 {leaf['code']} 产品数: {len(links)}")
                        self.logger.info(f"   地址: {leaf['url']}")
                    else:
                        self.stats['failed_leaves'].append(leaf['code'])
                        self.progress_tracker.update_task("产品链接提取", success=False)
                        self.logger.warning(f"⚠️  叶节点 {leaf['code']} 无产品")
                        self.logger.warning(f"   地址: {leaf['url']}")
                        
                except Exception as e:
                    self.logger.error(f"❌ 叶节点 {leaf['code']} 失败: {e}")
                    self.logger.error(f"   地址: {leaf['url']}")
                    all_results[leaf['code']] = []
                    self.stats['failed_leaves'].append(leaf['code'])
                    self.progress_tracker.update_task("产品链接提取", success=False)
                
                # 定期汇总当前进度
                if completed % 50 == 0 or completed == len(leaves):
                    total_products = sum(len(links) for links in all_results.values())
                    self.logger.info(f"\n当前累计产品链接数: {total_products}")
        

        
        # 产品链接提取汇总
        self.logger.info(f"\n✅ 产品链接提取完成:")
        self.logger.info(f"   • 成功叶节点: {self.stats['success_leaves']}/{len(leaves)}")
        self.logger.info(f"   • 失败叶节点: {len(self.stats['failed_leaves'])}")
        self.logger.info(f"   • 总产品数: {self.stats['total_products']} 个")
        
        return all_results
    
    def _crawl_specifications_parallel(self, 
                                     leaves: List[Dict], 
                                     leaf_products: Dict[str, List[str]]) -> List[Dict]:
        """并行爬取产品规格 (优化版)"""
        final_leaves = []
        
        # 准备所有产品URL及其所属叶节点
        all_product_tasks = []
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
                # 处理有产品的叶节点
                self.logger.info(f"处理叶节点 {code} 的 {len(product_urls)} 个产品")
                for url in product_urls:
                    all_product_tasks.append((url, leaf_info))
            
            final_leaves.append(leaf_info)
        
        # 注册任务
        self.progress_tracker.register_task("产品规格提取", len(all_product_tasks))
        
        # 并行处理所有产品
        if len(all_product_tasks) == 0:
            self.logger.warning("没有产品需要爬取规格")
            return final_leaves
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(
                    self.specifications_crawler.extract_specifications,
                    task[0]
                ): task
                for task in all_product_tasks
            }
            
            # 收集结果
            completed = 0
            for future in as_completed(future_to_task):
                url, leaf_info = future_to_task[future]
                completed += 1
                
                try:
                    spec_result = future.result()
                    
                    product_info = {
                        'product_url': spec_result['product_url'],
                        'specifications': spec_result['specifications'],
                        'success': spec_result['success']
                    }
                    
                    if not spec_result['success']:
                        product_info['error'] = spec_result.get('error', 'unknown')
                        self.stats['failed_products'].append(spec_result['product_url'])
                        self.progress_tracker.update_task("产品规格提取", success=False)
                    else:
                        self.stats['success_products'] += 1
                        self.stats['total_specifications'] += len(spec_result['specifications'])
                        self.progress_tracker.update_task("产品规格提取", success=True)
                        
                        # 显示具体的产品规格提取成功信息
                        if self.stats['success_products'] <= 5 or self.stats['success_products'] % 100 == 0:
                            self.logger.info(f"✅ [{self.stats['success_products']}/{len(all_product_tasks)}] "
                                           f"提取成功: {len(spec_result['specifications'])} 个规格 - {url}")
                    
                    leaf_info['products'].append(product_info)
                    
                    # 定期显示进度汇总
                    if completed % 500 == 0 or completed == len(all_product_tasks):
                        self.logger.info(f"\n进度汇总: {completed}/{len(all_product_tasks)} 产品已处理")
                        self.logger.info(f"成功: {self.stats['success_products']}, 失败: {len(self.stats['failed_products'])}")
                        
                except Exception as e:
                    self.logger.error(f"产品 {url} 规格提取失败: {e}")
                    leaf_info['products'].append({
                        'product_url': url,
                        'specifications': [],
                        'success': False,
                        'error': str(e)
                    })
                    self.stats['failed_products'].append(url)
                    self.progress_tracker.update_task("产品规格提取", success=False)
        

        
        # 产品规格爬取汇总
        self.logger.info(f"\n✅ 产品规格爬取完成:")
        self.logger.info(f"   • 成功产品: {self.stats['success_products']}/{len(all_product_tasks)}")
        self.logger.info(f"   • 失败产品: {len(self.stats['failed_products'])}")
        self.logger.info(f"   • 总规格数: {self.stats['total_specifications']} 个")
        
        return final_leaves
    
    def _save_results(self, root: Dict, leaves: List[Dict], output_file: str = None) -> Dict:
        """保存结果 (优化版)"""
        if not output_file:
            timestamp = int(time.time())
            output_file = f'results/products/optimized_pipeline_{timestamp}.json'
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = {
            'metadata': {
                'generated': datetime.now().isoformat(),
                'version': '3.0-optimized',
                'stats': self.stats
            },
            'root': root,
            'leaves': leaves
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"\n✅ 结果已保存到: {output_path.resolve()}")
        self.logger.info(f"   文件名: {output_path.name}")
        self.logger.info(f"   大小: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
        return result
    
    def _calculate_stats(self):
        """计算统计信息"""
        self.stats['end_time'] = datetime.now()
        self.stats['duration'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
    
    def _print_summary(self):
        """打印最终汇总"""
        duration_min = self.stats['duration'] / 60
        
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 爬取完成 - 最终统计")
        self.logger.info("="*60)
        
        # 时间统计
        self.logger.info(f"⏱️  总耗时: {duration_min:.1f} 分钟")
        
        # 数据统计
        self.logger.info(f"\n📈 数据统计:")
        self.logger.info(f"   • 叶节点: {self.stats['total_leaves']} 个")
        self.logger.info(f"   • 产品数: {self.stats['total_products']} 个")
        self.logger.info(f"   • 规格数: {self.stats['total_specifications']} 个")
        
        # 成功率统计
        leaf_success_rate = (self.stats['success_leaves'] / self.stats['total_leaves'] * 100) if self.stats['total_leaves'] > 0 else 0
        self.logger.info(f"\n📊 成功率:")
        self.logger.info(f"   • 叶节点成功率: {leaf_success_rate:.1f}% ({self.stats['success_leaves']}/{self.stats['total_leaves']})")
        self.logger.info(f"   • 产品成功: {self.stats['success_products']} 个")
        self.logger.info(f"   • 产品失败: {len(self.stats['failed_products'])} 个")
        
        self.logger.info("="*60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TraceParts 优化版完整爬取流水线')
    parser.add_argument('--workers', type=int, default=32, help='最大并发数 (默认: 32)')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径')
    parser.add_argument('--no-cache', action='store_true', help='禁用缓存')
    
    args = parser.parse_args()
    
    # 不再设置basicConfig，让ThreadSafeLogger完全控制日志输出
    # 运行优化版流水线
    pipeline = OptimizedFullPipeline(max_workers=args.workers)
    
    pipeline.run(
        output_file=args.output,
        cache_enabled=not args.no_cache
    )


if __name__ == '__main__':
    main() 