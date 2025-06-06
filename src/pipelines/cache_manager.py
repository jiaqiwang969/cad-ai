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
import os
import threading

# 添加项目根目录到路径
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.crawler.classification_enhanced import EnhancedClassificationCrawler
from src.crawler.ultimate_products_v2 import UltimateProductLinksCrawlerV2 as UltimateProductLinksCrawler
from src.crawler.specifications_optimized import OptimizedSpecificationsCrawler
from src.utils.thread_safe_logger import ThreadSafeLogger, ProgressTracker


def _crawl_single_leaf_product_worker(args: dict) -> dict:
    """
    多进程 worker 函数：处理单个叶节点的产品链接爬取
    
    Args:
        args: 包含叶节点信息和配置的字典
    
    Returns:
        dict: 包含叶节点代码、产品列表和错误信息的结果字典
    """
    import sys
    import os
    import json
    import time
    from pathlib import Path
    
    # 从参数中提取信息
    leaf = args['leaf']
    cache_dir = Path(args['cache_dir'])
    cache_ttl_hours = args['cache_ttl_hours']
    debug_mode = args.get('debug_mode', False)
    
    leaf_code = leaf['code']
    leaf_url = leaf['url']
    
    # 结果字典
    result = {
        'leaf_code': leaf_code,
        'products': [],
        'from_cache': False,
        'error_info': None
    }
    
    try:
        # 检查缓存
        cache_file = cache_dir / f"{leaf_code}.json"
        
        if cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < cache_ttl_hours * 3600:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    products = json.load(f)
                
                # 检查缓存内容是否有效（非空）
                if products and len(products) > 0:
                    result['products'] = products
                    result['from_cache'] = True
                    print(f"📦 [进程] 使用有效缓存: {leaf_code} ({len(products)} 个产品)")
                    return result
                else:
                    print(f"⚠️ [进程] 发现空缓存: {leaf_code}，将重新爬取")
        
        # 需要爬取新数据 - 导入爬取器
        # 注意：需要确保模块路径正确
        current_dir = Path(__file__).parent.parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        
        from crawler.ultimate_products_v2 import UltimateProductLinksCrawlerV2
        
        print(f"🌐 [进程] 开始爬取: {leaf_code}")
        print(f"🔗 [进程] URL: {leaf_url}")
        
        # 创建爬取器实例
        crawler = UltimateProductLinksCrawlerV2(
            headless=True,
            debug_mode=debug_mode
        )
        
        # 爬取产品链接
        with crawler:
            products, progress_info = crawler.collect_all_product_links(leaf_url)
            
            # 记录进度信息
            target_count = progress_info.get('target_count_on_page', 0)
            if target_count > 0:
                print(f"📊 [进程] 抓取完成度: {progress_info['progress_percentage']}% ({progress_info['extracted_count']}/{target_count})")
        
        result['products'] = products
        
        # 保存缓存
        cache_dir.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"✅ [进程] 完成: {leaf_code} ({len(products)} 个产品)")
        
        # 记录空产品情况
        if not products:
            result['error_info'] = {
                'error_type': 'zero_products_no_exception',
                'leaf_code': leaf_code,
                'leaf_name': leaf.get('name', ''),
                'leaf_url': leaf_url,
                'product_count': 0,
                'note': '爬取完成但返回空产品列表'
            }
        
    except Exception as e:
        print(f"❌ [进程] 失败: {leaf_code} - {e}")
        
        # 记录错误信息
        result['error_info'] = {
            'error_type': 'product_extraction_exception',
            'leaf_code': leaf_code,
            'leaf_name': leaf.get('name', ''),
            'leaf_url': leaf_url,
            'exception': str(e),
            'exception_type': type(e).__name__,
            'note': '产品链接爬取过程中发生异常'
        }
        result['products'] = []
    
    return result


class CacheLevel(Enum):
    """缓存级别枚举"""
    NONE = 0
    CLASSIFICATION = 1  # 仅分类树
    PRODUCTS = 2       # 分类树 + 产品链接
    SPECIFICATIONS = 3  # 分类树 + 产品链接 + 产品规格


class CacheManager:
    """统一的缓存管理器"""
    
    def __init__(self, cache_dir: str = 'results/cache', max_workers: int = 16, debug_mode: bool = False):
        self.cache_dir = Path(cache_dir)
        self.max_workers = max_workers
        self.logger = ThreadSafeLogger("cache-manager", logging.INFO)
        self.progress_tracker = ProgressTracker(self.logger)
        self.debug_mode = debug_mode
        
        # 缓存文件路径 - 新的命名规范
        self.cache_index_file = self.cache_dir / 'cache_index.json'  # 索引文件，记录最新版本
        self.products_cache_dir = self.cache_dir / 'products'
        self.specs_cache_dir = self.cache_dir / 'specifications'
        self.error_logs_dir = self.cache_dir / 'error_logs'  # 异常记录目录
        
        # 创建版本化的缓存文件名
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.classification_file = self.cache_dir / f'classification_tree_v{self.timestamp}.json'
        self.products_file = self.cache_dir / f'products_links_v{self.timestamp}.json'  
        self.specifications_file = self.cache_dir / f'specifications_v{self.timestamp}.json'
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.products_cache_dir.mkdir(parents=True, exist_ok=True)
        self.specs_cache_dir.mkdir(parents=True, exist_ok=True)
        self.error_logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 失败规格记录文件 (jsonl)
        self.failed_specs_file = self.cache_dir / 'failed_specs.jsonl'
        self.failed_lock = threading.Lock()
        
        # 初始化时清理重复的失败记录
        self._cleanup_duplicate_failed_specs()
        
        # 初始化爬取器
        self.classification_crawler = EnhancedClassificationCrawler()
        # 使用新的v2版本，集成test-08的所有优化策略
        from ..crawler.ultimate_products_v2 import UltimateProductLinksCrawlerV2
        self.products_crawler = UltimateProductLinksCrawlerV2(headless=True)  # 使用无头模式
        self.specifications_crawler = OptimizedSpecificationsCrawler(log_level=logging.INFO)
        
        # 缓存有效期（小时）
        self.cache_ttl = {
            CacheLevel.CLASSIFICATION: 24 * 7,  # 分类树：7天
            CacheLevel.PRODUCTS: 24 * 3,       # 产品链接：3天
            CacheLevel.SPECIFICATIONS: 24      # 产品规格：1天
        }
        
        # 异常记录
        self.error_records = {
            'products': [],      # 产品链接爬取失败记录
            'specifications': [] # 产品规格爬取失败记录
        }
    
    def get_cache_level(self) -> Tuple[CacheLevel, Optional[Dict]]:
        """获取当前缓存级别和缓存数据"""
        # 读取缓存索引文件
        if not self.cache_index_file.exists():
            # 如果没有索引文件，检查是否有旧版本的缓存文件
            old_cache_file = self.cache_dir / 'classification_tree_full.json'
            if old_cache_file.exists():
                self.logger.info("🔄 检测到旧版本缓存文件，将进行迁移")
                try:
                    with open(old_cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    metadata = data.get('metadata', {})
                    cache_level = CacheLevel(metadata.get('cache_level', 1))
                    return cache_level, data
                except Exception as e:
                    self.logger.error(f"读取旧版本缓存失败: {e}")
            return CacheLevel.NONE, None
        
        try:
            with open(self.cache_index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            latest_files = index_data.get('latest_files', {})
            current_level = CacheLevel.NONE
            data = None
            
            # 按优先级检查缓存文件是否存在
            if 'specifications' in latest_files:
                specs_file = self.cache_dir / latest_files['specifications']
                if specs_file.exists():
                    current_level = CacheLevel.SPECIFICATIONS
                    with open(specs_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # === 新增: 检查规格数，如为 0 则降级 ===
                    try:
                        meta = data.get('metadata', {})
                        if meta.get('total_specifications', 0) == 0:
                            self.logger.warning("检测到规格缓存文件缺少规格数据，将降级为 PRODUCTS 级别重新爬取")
                            current_level = CacheLevel.PRODUCTS
                    except Exception:
                        pass
            elif 'products' in latest_files:
                products_file = self.cache_dir / latest_files['products']
                if products_file.exists():
                    current_level = CacheLevel.PRODUCTS
                    with open(products_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
            elif 'classification' in latest_files:
                class_file = self.cache_dir / latest_files['classification']
                if class_file.exists():
                    current_level = CacheLevel.CLASSIFICATION
                    with open(class_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
            
            # 检查缓存是否过期
            if data and 'metadata' in data:
                metadata = data['metadata']
            if 'generated' in metadata:
                generated_time = datetime.fromisoformat(metadata['generated'])
                age_hours = (datetime.now() - generated_time).total_seconds() / 3600
                
                if age_hours > self.cache_ttl.get(current_level, 24):
                    self.logger.warning(f"缓存已过期 (年龄: {age_hours:.1f}小时)")
                    return CacheLevel.NONE, None
            
            return current_level, data
            
        except Exception as e:
            self.logger.error(f"读取缓存索引失败: {e}")
            return CacheLevel.NONE, None
    
    def _update_cache_index(self, level: CacheLevel, filename: str):
        """更新缓存索引文件"""
        index_data = {}
        if self.cache_index_file.exists():
            try:
                with open(self.cache_index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            except Exception:
                pass
        
        if 'latest_files' not in index_data:
            index_data['latest_files'] = {}
        if 'version_history' not in index_data:
            index_data['version_history'] = []
        
        # 更新最新文件记录
        level_name = level.name.lower()
        index_data['latest_files'][level_name] = filename
        
        # 添加版本历史
        version_record = {
            'level': level.name,
            'filename': filename,
            'timestamp': datetime.now().isoformat(),
            'version': self.timestamp
        }
        index_data['version_history'].append(version_record)
        
        # 只保留最近50个版本记录
        if len(index_data['version_history']) > 50:
            index_data['version_history'] = index_data['version_history'][-50:]
        
        # 保存索引文件
        with open(self.cache_index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"📇 已更新缓存索引: {level.name} -> {filename}")
    
    def save_cache(self, data: Dict, level: CacheLevel):
        """保存缓存数据"""
        # 选择对应的文件名
        if level == CacheLevel.CLASSIFICATION:
            cache_file = self.classification_file
        elif level == CacheLevel.PRODUCTS:
            cache_file = self.products_file
        elif level == CacheLevel.SPECIFICATIONS:
            cache_file = self.specifications_file
        else:
            raise ValueError(f"未知的缓存级别: {level}")
        
        # 备份现有文件（如果存在）
        if cache_file.exists():
            backup_file = cache_file.with_suffix('.json.bak')
            cache_file.rename(backup_file)
            self.logger.info(f"📋 已备份原文件到: {backup_file}")
        
        try:
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
                'version': f'v{self.timestamp}',
                'total_leaves': len(data.get('leaves', [])),
                'total_products': sum(leaf.get('product_count', 0) for leaf in data.get('leaves', [])),
                'total_specifications': total_specifications
            }
            
            # 保存文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            file_size_mb = cache_file.stat().st_size / 1024 / 1024
            self.logger.info(f"💾 已保存缓存到: {cache_file}")
            self.logger.info(f"   缓存级别: {level.name}")
            self.logger.info(f"   文件大小: {file_size_mb:.1f} MB")
            self.logger.info(f"   版本号: v{self.timestamp}")
            
            # 更新索引文件
            self._update_cache_index(level, cache_file.name)
            
            # 清理旧版本文件（保留最近5个版本）
            self._cleanup_old_versions(level)
            
        except Exception as e:
            self.logger.error(f"保存缓存失败: {e}")
    
    def _cleanup_old_versions(self, level: CacheLevel, keep_versions: int = 5):
        """清理旧版本的缓存文件，只保留最近的几个版本"""
        try:
            # 根据级别确定文件模式
            if level == CacheLevel.CLASSIFICATION:
                pattern = "classification_tree_v*.json"
            elif level == CacheLevel.PRODUCTS:
                pattern = "products_links_v*.json"
            elif level == CacheLevel.SPECIFICATIONS:
                pattern = "specifications_v*.json"
            else:
                return
            
            # 查找所有匹配的文件
            cache_files = list(self.cache_dir.glob(pattern))
            if len(cache_files) <= keep_versions:
                return
            
            # 按修改时间排序，删除较旧的文件
            cache_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            files_to_delete = cache_files[keep_versions:]
            
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    self.logger.debug(f"🗑️ 已删除旧版本文件: {file_path.name}")
                except Exception as e:
                    self.logger.warning(f"删除旧文件失败 {file_path.name}: {e}")
            
            if files_to_delete:
                self.logger.info(f"🧹 已清理 {len(files_to_delete)} 个旧版本文件")
                
        except Exception as e:
            self.logger.warning(f"清理旧版本文件失败: {e}")
    
    def get_version_history(self, level: Optional[CacheLevel] = None) -> List[Dict]:
        """获取版本历史记录"""
        try:
            if not self.cache_index_file.exists():
                return []
            
            with open(self.cache_index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            history = index_data.get('version_history', [])
            
            # 如果指定了级别，只返回该级别的历史
            if level:
                history = [h for h in history if h.get('level') == level.name]
            
            # 按时间倒序排列（最新的在前）
            history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return history
            
        except Exception as e:
            self.logger.error(f"获取版本历史失败: {e}")
            return []
    
    def get_cache_status(self) -> Dict:
        """获取详细的缓存状态信息"""
        current_level, data = self.get_cache_level()
        
        status = {
            'current_level': current_level.name,
            'current_level_value': current_level.value,
            'cache_directory': str(self.cache_dir),
            'latest_files': {},
            'file_sizes': {},
            'metadata': {}
        }
        
        # 读取索引文件获取最新文件信息
        try:
            if self.cache_index_file.exists():
                with open(self.cache_index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                latest_files = index_data.get('latest_files', {})
                for level_name, filename in latest_files.items():
                    file_path = self.cache_dir / filename
                    if file_path.exists():
                        status['latest_files'][level_name] = filename
                        status['file_sizes'][level_name] = f"{file_path.stat().st_size / 1024 / 1024:.1f} MB"
        except Exception as e:
            self.logger.warning(f"读取缓存索引状态失败: {e}")
        
        # 如果有当前数据，提取元数据
        if data and 'metadata' in data:
            status['metadata'] = data['metadata']
        
        return status
    
    def _record_error(self, error_type: str, error_info: Dict):
        """记录错误信息（确保唯一性，同一个叶节点只记录最新错误）"""
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'version': f'v{self.timestamp}',
            **error_info
        }
        
        if error_type in self.error_records:
            # 检查是否已存在相同叶节点的错误记录
            leaf_code = error_info.get('leaf_code')
            if leaf_code and error_type == 'products':
                # 移除该叶节点的旧记录（如果存在）
                self.error_records[error_type] = [
                    record for record in self.error_records[error_type] 
                    if record.get('leaf_code') != leaf_code
                ]
            
            # 添加新记录
            self.error_records[error_type].append(error_record)
    
    def _save_error_logs(self):
        """保存异常记录到文件"""
        if not any(self.error_records.values()):
            return  # 没有错误记录，不需要保存
        
        error_log_file = self.error_logs_dir / f'error_log_v{self.timestamp}.json'
        
        # 统计信息
        error_summary = {
            'generated': datetime.now().isoformat(),
            'version': f'v{self.timestamp}',
            'summary': {
                'total_product_errors': len(self.error_records['products']),
                'total_specification_errors': len(self.error_records['specifications']),
                'zero_specs_count': len([e for e in self.error_records['specifications'] if e.get('spec_count', 0) == 0]),
                'exception_count': len([e for e in self.error_records['specifications'] if 'exception' in e])
            },
            'details': self.error_records
        }
        
        # 保存错误日志
        with open(error_log_file, 'w', encoding='utf-8') as f:
            json.dump(error_summary, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"📝 异常记录已保存: {error_log_file}")
        self.logger.info(f"   • 产品链接失败: {error_summary['summary']['total_product_errors']} 个")
        self.logger.info(f"   • 规格爬取失败: {error_summary['summary']['total_specification_errors']} 个")
        self.logger.info(f"   • 其中零规格: {error_summary['summary']['zero_specs_count']} 个")
    
    def extend_to_products(self, data: Dict) -> Dict:
        """扩展缓存到产品链接级别（自动智能重试失败记录）"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📦 扩展缓存：添加产品链接")
        self.logger.info("="*60)
        
        # 加载失败记录（从错误日志，最多重试3次，防止死循环）
        failed_products_db = self._load_failed_products_from_error_logs(max_retry_times=3)
        
        # 失败记录统计
        if failed_products_db:
            tries_stats = {}
            for record in failed_products_db.values():
                tries = record.get('tries', 1)
                tries_stats[tries] = tries_stats.get(tries, 0) + 1
            
            self.logger.info(f"📋 检测到失败产品记录: 共 {len(failed_products_db)} 个失败叶节点")
            for tries in sorted(tries_stats.keys()):
                self.logger.info(f"   • 失败 {tries} 次: {tries_stats[tries]} 个叶节点")
        else:
            self.logger.info("📋 失败产品记录: 无失败记录")
        
        # 智能构建处理列表：分别处理失败的叶节点和正常叶节点
        all_leaves = data['leaves']
        priority_failed_leaves = []
        normal_leaves = []
        
        # 先添加失败的叶节点进行重试
        failed_leaf_codes = set(failed_products_db.keys())
        for leaf in all_leaves:
            if leaf['code'] in failed_leaf_codes:
                leaf['is_retry'] = True
                leaf['previous_tries'] = failed_products_db[leaf['code']].get('tries', 0)
                priority_failed_leaves.append(leaf)
            else:
                normal_leaves.append(leaf)
        
        if priority_failed_leaves:
            self.logger.info(f"🔄 优先重试失败叶节点: {len(priority_failed_leaves)} 个")
        if normal_leaves:
            self.logger.info(f"📋 正常处理叶节点: {len(normal_leaves)} 个")
        
        if not priority_failed_leaves and not normal_leaves:
            self.logger.info("⚪️ 没有需要处理的叶节点")
            return data
        
        # 总计任务数
        total_leaves = len(priority_failed_leaves) + len(normal_leaves)
        self.progress_tracker.register_task("产品链接扩展", total_leaves)
        
        # 第一阶段：优先并行处理失败重试的叶节点
        leaf_products = {}
        
        if priority_failed_leaves:
            self.logger.info(f"\n📍 [阶段 1/2] 并行重试失败叶节点")
            self.logger.info("-" * 50)
            
            # 失败重试总是使用并行（除非只有1个）
            use_parallel_retry = self.max_workers > 1 and len(priority_failed_leaves) > 1
            
            if use_parallel_retry:
                retry_workers = min(self.max_workers//2, len(priority_failed_leaves), 8)  # 为失败重试分配一半进程
                self.logger.info(f"🚀 并行重试模式: {len(priority_failed_leaves)} 个失败叶节点（{retry_workers} 进程）")
                retry_results = self._crawl_products_parallel(priority_failed_leaves, max_processes=retry_workers)
            else:
                self.logger.info(f"🔄 串行重试模式: {len(priority_failed_leaves)} 个失败叶节点")
                retry_results = self._crawl_products_serial(priority_failed_leaves)
            
            # 合并重试结果
            leaf_products.update(retry_results)
            
            # 统计重试成功情况
            successful_retries = []
            for leaf_code, products in retry_results.items():
                if products and len(products) > 0:
                    successful_retries.append(leaf_code)
            
            if successful_retries:
                self.logger.info(f"🎉 重试成功: {len(successful_retries)} 个叶节点修复")
            
            retry_failures = len(priority_failed_leaves) - len(successful_retries)
            if retry_failures > 0:
                self.logger.info(f"⚠️  重试仍失败: {retry_failures} 个叶节点")
        
        # 第二阶段：处理正常叶节点
        if normal_leaves:
            self.logger.info(f"\n📍 [阶段 2/2] 处理正常叶节点")
            self.logger.info("-" * 50)
            
            # 选择处理模式：并行 vs 串行
            use_parallel_normal = self.max_workers > 1 and len(normal_leaves) > 3
            
            if use_parallel_normal:
                normal_workers = min(self.max_workers, len(normal_leaves), 8)  # 正常处理可以使用全部进程
                self.logger.info(f"🚀 并行处理 {len(normal_leaves)} 个正常叶节点（{normal_workers} 进程）")
                normal_results = self._crawl_products_parallel(normal_leaves, max_processes=normal_workers)
            else:
                self.logger.info(f"🔄 串行处理 {len(normal_leaves)} 个正常叶节点")
                normal_results = self._crawl_products_serial(normal_leaves)
            
            # 合并正常结果
            leaf_products.update(normal_results)
        
        # 更新数据结构
        self._update_tree_with_products(data, leaf_products)
        
        # 统计
        total_products = sum(len(products) for products in leaf_products.values())
        productive_leaves = sum(1 for products in leaf_products.values() if len(products) > 0)
        total_processed = len(priority_failed_leaves) + len(normal_leaves)
        empty_leaves = total_processed - productive_leaves
        zero_product_errors = len([e for e in self.error_records['products'] if e.get('error_type') == 'zero_products'])
        failed_errors = len([e for e in self.error_records['products'] if e.get('error_type') == 'product_extraction_failed'])
        
        self.logger.info(f"\n✅ 产品链接扩展完成:")
        self.logger.info(f"   • 处理叶节点: {total_processed} 个")
        if total_processed > 0:
            self.logger.info(f"   • 有效叶节点: {productive_leaves} 个 ({productive_leaves/total_processed*100:.1f}%)")
        else:
            self.logger.info(f"   • 有效叶节点: {productive_leaves} 个 (0.0%)")
        self.logger.info(f"   • 空叶节点: {zero_product_errors} 个 (无产品)")
        self.logger.info(f"   • 失败叶节点: {failed_errors} 个 (爬取异常)")
        self.logger.info(f"   • 总产品数: {total_products} 个")
        if productive_leaves > 0:
            self.logger.info(f"   • 平均每个有效叶节点: {total_products/productive_leaves:.1f} 个产品")
        
        # 添加分阶段统计
        if priority_failed_leaves:
            retry_success = sum(1 for leaf in priority_failed_leaves if leaf_products.get(leaf['code'], []))
            self.logger.info(f"   📊 重试统计: {retry_success}/{len(priority_failed_leaves)} 个失败叶节点修复")
        if normal_leaves:
            normal_success = sum(1 for leaf in normal_leaves if leaf_products.get(leaf['code'], []))
            self.logger.info(f"   📊 正常统计: {normal_success}/{len(normal_leaves)} 个叶节点成功")
        
        # 保存异常记录（如果有的话）
        if self.error_records['products']:
            self._save_error_logs()
        
        return data
    
    def extend_to_specifications(self, data: Dict, retry_failed_only: bool = False) -> Dict:
        """扩展缓存到产品规格级别"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📋 扩展缓存：添加产品规格")
        self.logger.info("="*60)
        
        failed_db = self._load_failed_specs()
        
        # 获取当前已缓存的规格数量
        existing_cache_count = self._get_cached_specs_count()
        self.logger.info(f"📊 当前已缓存规格文件: {existing_cache_count} 个")
        
        # 失败记录统计
        if failed_db:
            tries_stats = {}
            for record in failed_db.values():
                tries = record.get('tries', 1)
                tries_stats[tries] = tries_stats.get(tries, 0) + 1
            
            self.logger.info(f"📋 失败记录统计: 共 {len(failed_db)} 个失败URL")
            for tries in sorted(tries_stats.keys()):
                self.logger.info(f"   • 失败 {tries} 次: {tries_stats[tries]} 个URL")
        else:
            self.logger.info("📋 失败记录: 无失败记录")
        
        # build product list
        if retry_failed_only:
            self.logger.info("🔄 仅重试模式：只处理失败的产品")
            product_urls = list(failed_db.keys())
            all_products = [{'product_url': u, 'leaf_code': failed_db[u].get('leaf','unknown')} for u in product_urls]
        else:
            # 优先处理失败产品 + 智能过滤
            self.logger.info("🔍 收集需要处理的产品...")
            all_products = []
            skipped_cached = 0
            skipped_failed = 0
            
            # === 新增：优先添加失败的产品进行重试 ===
            priority_failed = 0
            failed_urls_added = set()  # 记录已添加的失败URL
            for failed_url, failed_record in failed_db.items():
                # 失败产品优先重试，不受次数限制
                leaf_code = failed_record.get('leaf', 'unknown')
                all_products.append({
                    'product_url': failed_url, 
                    'leaf_code': leaf_code,
                    'is_retry': True,  # 标记为重试产品
                    'previous_tries': failed_record.get('tries', 0)
                })
                failed_urls_added.add(failed_url)
                priority_failed += 1
            
            if priority_failed > 0:
                self.logger.info(f"📋 优先处理失败产品: {priority_failed} 个")
            
            for leaf in data['leaves']:
                leaf_code = leaf['code']
                
                for product_url in leaf.get('products', []):
                    if isinstance(product_url, str):
                        product_info = {'product_url': product_url, 'leaf_code': leaf_code}
                    else:
                        # 处理字典格式的产品（可能来自 SPECIFICATIONS 级别的缓存）
                        product_info = product_url.copy() if isinstance(product_url, dict) else {'product_url': str(product_url)}
                        product_info['leaf_code'] = leaf_code
                    
                    product_url_str = product_info['product_url']
                    
                    # 1. 检查是否已经成功缓存
                    if self._is_product_cached(product_url_str, leaf_code):
                        skipped_cached += 1
                        continue
                    
                    # 2. 如果已经在失败列表中，跳过（因为已经在上面优先处理了）
                    if product_url_str in failed_urls_added:
                        skipped_failed += 1
                        continue
                    
                    # 3. 添加到处理列表
                    all_products.append(product_info)
            
            # 计算新产品数量
            new_products = len(all_products) - priority_failed
            
            self.logger.info(f"📋 智能过滤结果:")
            self.logger.info(f"   • 优先重试失败: {priority_failed} 个")
            self.logger.info(f"   • 跳过已缓存: {skipped_cached} 个")
            self.logger.info(f"   • 跳过重复失败: {skipped_failed} 个") 
            self.logger.info(f"   • 新产品待处理: {new_products} 个")
            self.logger.info(f"   • 需要处理总计: {len(all_products)} 个")

        # 如果没有产品需要处理，直接返回
        if len(all_products) == 0:
            self.logger.info("✅ 所有产品规格都已缓存，无需重新爬取")
            return data
        
        self.logger.info(f"准备爬取 {len(all_products)} 个产品的规格…")
        
        # 显示预估节省的时间
        if not retry_failed_only and (skipped_cached > 0 or skipped_failed > 0):
            total_skipped = skipped_cached + skipped_failed
            estimated_time_saved = total_skipped * 15 / 60  # 假设每个产品15秒，转换为分钟
            self.logger.info(f"⚡ 智能跳过节省预估时间: {estimated_time_saved:.1f} 分钟")
        
        # 恢复原版线程池处理，但保持实时写入优化
        self.logger.info(f"开始并行提取产品规格 (线程数: {min(len(all_products), self.max_workers)})")
        
        # 处理结果
        product_specs = {}
        success_count = 0
        total_specs = 0
        processed_count = 0
        
        # 使用线程池并行处理，但实时处理结果
        with ThreadPoolExecutor(max_workers=min(len(all_products), self.max_workers)) as executor:
            # 提交所有任务
            future_to_product = {
                executor.submit(self.specifications_crawler.extract_specifications, p['product_url'] if isinstance(p, dict) else p): p
                for p in all_products
            }
            
            # 实时处理完成的任务
            for future in as_completed(future_to_product):
                product_info = future_to_product[future]
                product_url = product_info['product_url'] if isinstance(product_info, dict) else product_info
                
                try:
                    result = future.result()
                except Exception as e:
                    self.logger.error(f"❌ 规格提取异常: {e} | url={product_url}")
                    result = {
                        'product_url': product_url,
                        'specifications': [],
                        'count': 0,
                        'success': False,
                        'error': str(e)
                    }
                
                # 以下是原有的处理逻辑，但现在是实时执行
                specs = result.get('specifications', [])
                
                # 调试：打印原始数据结构
                if specs and len(specs) > 0:
                    self.logger.debug(f"📊 规格数据样例: {specs[0] if isinstance(specs[0], dict) else specs[:3]}")
                
                # 新增: 详细日志，记录每个产品的规格提取结果
                retry_info = ""
                if isinstance(product_info, dict) and product_info.get('is_retry'):
                    retry_info = f" (重试{product_info.get('previous_tries', 0)}次)"
                
                self.logger.info(
                    f"🔍 规格提取结果 | {'✅ 成功' if specs else '⚠️ 无规格' if result.get('success') else '❌ 失败'} | "
                    f"specs={len(specs)}{retry_info} | url={product_url}"
                )
                product_specs[product_url] = specs
                
                # 调试：如果找不到 product_info
                if not product_info:
                    self.logger.warning(f"⚠️ 找不到产品信息: {product_url}")
                    self.logger.debug(f"   all_products 样本: {all_products[:2] if all_products else 'empty'}")
                
                if result.get('success', False):
                    success_count += 1
                    total_specs += len(specs)
                    if len(specs)==0:
                        # zero spec -> treat as failure record
                        rec = {
                            'url': product_url,
                            'leaf': product_info.get('leaf_code','unknown') if isinstance(product_info,dict) else 'unknown',
                            'reason': 'ZeroSpecifications',
                            'tries': failed_db.get(product_url,{}).get('tries',0)+1,
                            'ts': datetime.now().isoformat()
                        }
                        self._append_failed_spec(rec)
                    else:
                        # 成功且有规格数据，从失败记录中移除
                        if product_url in failed_db:
                            prev_tries = failed_db[product_url].get('tries', 0)
                            self._remove_from_failed_specs(product_url)
                            self.logger.info(f"🎉 成功修复！已从失败记录中清理: {product_url} (之前失败 {prev_tries} 次)")
                        else:
                            self.logger.debug(f"✅ 新产品成功提取规格: {len(specs)} 个")
                else:
                    prev_tries = failed_db.get(product_url,{}).get('tries',0)
                    new_tries = prev_tries + 1
                    rec = {
                        'url': product_url,
                        'leaf': product_info.get('leaf_code','unknown') if isinstance(product_info,dict) else 'unknown',
                        'reason': result.get('error','Exception'),
                        'tries': new_tries,
                        'ts': datetime.now().isoformat()
                    }
                    
                    if product_url in failed_db:
                        self.logger.warning(f"⚠️ 重试仍失败: {product_url} (第 {new_tries} 次失败, 原因: {rec['reason']})")
                    else:
                        self.logger.warning(f"❌ 新增失败记录: {product_url} (原因: {rec['reason']})")
                    
                    self._append_failed_spec(rec)
                
                # END of failure branch

                # === 按产品立即写入规格缓存文件（成功或失败均尝试，避免遗漏） ===
                try:
                    import hashlib, json as _json
                    from urllib.parse import urlparse, parse_qs
                    
                    leaf_code_tmp = 'unknown'
                    if product_info and isinstance(product_info, dict):
                        leaf_code_tmp = product_info.get('leaf_code', 'unknown')
                    # 调试：确保我们知道 leaf_code    
                    self.logger.debug(f"📍 产品 {product_url[:50]}... -> leaf_code={leaf_code_tmp}")
                    url_hash_tmp = hashlib.md5(product_url.encode()).hexdigest()[:12]
                    base_name = f"{leaf_code_tmp}_{url_hash_tmp}"
                    
                    # 仅在成功且拿到规格时写入文件，避免空文件占位
                    if specs:
                        # 确保目录存在
                        self.specs_cache_dir.mkdir(parents=True, exist_ok=True)
                        
                        # === 生成多格式输出文件（模仿test-09-1） ===
                        
                        # 1. 解析产品URL获取基础信息
                        parsed_url = urlparse(product_url)
                        query_params = parse_qs(parsed_url.query)
                        product_name = parsed_url.path.split('/')[-1] if parsed_url.path else 'unknown'
                        
                        # 2. 构造完整JSON格式
                        complete_data = {
                            "extraction_info": {
                                "timestamp": int(time.time()),
                                "extraction_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                "base_product_url": product_url,
                                "total_specifications_found": len(specs),
                                "leaf_code": leaf_code_tmp,
                                "source": "pipeline-v2"
                            },
                            "base_product_info": {
                                "base_url": f"{parsed_url.scheme}://{parsed_url.netloc}",
                                "base_path": parsed_url.path,
                                "base_product_name": product_name,
                                "catalog_path": query_params.get('CatalogPath', [''])[0],
                                "product_id": query_params.get('Product', [''])[0],
                                "query_params": query_params
                            },
                            "product_specifications": specs,
                            "summary": {
                                "series_distribution": {},
                                "specification_samples": []
                            }
                        }
                        
                        # 3. 构造简化JSON格式
                        simplified_data = {
                            "extraction_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "total_count": len(specs),
                            "leaf_code": leaf_code_tmp,
                            "base_url": product_url,
                            "specifications": []
                        }
                        
                        # 4. 构造URL列表文本
                        url_lines = [
                            f"# 产品规格链接列表",
                            f"# 基础产品: {product_url}",
                            f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            f"# 叶节点: {leaf_code_tmp}",
                            f"# 找到 {len(specs)} 个规格",
                            ""
                        ]
                        
                        # 处理每个规格
                        for i, spec in enumerate(specs, 1):
                            if isinstance(spec, dict):
                                ref = spec.get('reference', f'spec_{i}')
                                dims = spec.get('dimensions', '')
                                weight = spec.get('weight', '')
                                
                                # 更新摘要信息
                                series = ref.split()[0] if ref else f'series_{i}'
                                complete_data["summary"]["series_distribution"][series] = complete_data["summary"]["series_distribution"].get(series, 0) + 1
                                
                                if i <= 10:  # 只保留前10个样例
                                    complete_data["summary"]["specification_samples"].append({
                                        "index": i,
                                        "reference": ref,
                                        "dimensions": dims,
                                        "weight": weight
                                    })
                                
                                # 添加到简化格式
                                simplified_data["specifications"].append({
                                    "id": i,
                                    "reference": ref,
                                    "dimensions": dims,
                                    "weight": weight,
                                    "series": series
                                })
                                
                                # 添加到URL列表
                                url_lines.append(f"# {ref} ({dims})")
                                url_lines.append(f"# Spec {i}: {ref}")
                                url_lines.append("")
                        
                        # 写入三种格式的文件
                        complete_path = self.specs_cache_dir / f"{base_name}_complete.json"
                        simplified_path = self.specs_cache_dir / f"{base_name}_list.json"
                        urls_path = self.specs_cache_dir / f"{base_name}_urls.txt"
                        
                        # 保存完整JSON
                        with open(complete_path, 'w', encoding='utf-8') as f:
                            _json.dump(complete_data, f, ensure_ascii=False, indent=2)
                        
                        # 保存简化JSON
                        with open(simplified_path, 'w', encoding='utf-8') as f:
                            _json.dump(simplified_data, f, ensure_ascii=False, indent=2)
                        
                        # 保存URL文本
                        with open(urls_path, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(url_lines))
                        
                        # 同时保留原始格式（向后兼容）
                        cache_path_tmp = self.specs_cache_dir / f"{base_name}.json"
                        with open(cache_path_tmp, 'w', encoding='utf-8') as f:
                            _json.dump(specs, f, ensure_ascii=False, indent=2)
                        
                        self.logger.info(f"💾 写入规格缓存文件: {base_name} ({len(specs)} specs, 4 formats)")
                        self.logger.debug(f"   • 完整格式: {complete_path.name}")
                        self.logger.debug(f"   • 简化格式: {simplified_path.name}")
                        self.logger.debug(f"   • URL列表: {urls_path.name}")
                        self.logger.debug(f"   • 原始格式: {cache_path_tmp.name}")
                        
                        # 验证文件是否真的写入
                        for file_path in [complete_path, simplified_path, urls_path, cache_path_tmp]:
                            if file_path.exists():
                                file_size = file_path.stat().st_size
                                self.logger.debug(f"✅ {file_path.name}: {file_size} bytes")
                            else:
                                self.logger.error(f"❌ 文件写入后不存在！{file_path}")
                    else:
                        self.logger.debug(f"⚠️ 跳过空规格: {product_url}")
                except Exception as _e:
                    self.logger.error(f"❌ 写入规格缓存文件失败: {_e}", exc_info=True)
        
        # 更新数据结构
        self._update_tree_with_specifications(data, product_specs)
        
        # 最终缓存统计
        final_cache_count = self._get_cached_specs_count()
        newly_cached = final_cache_count - existing_cache_count
        
        # 统计 
        self.logger.info(f"\n✅ 产品规格扩展完成:")
        self.logger.info(f"   • 处理产品: {len(all_products)} 个")
        self.logger.info(f"   • 成功爬取: {success_count} 个")
        self.logger.info(f"   • 总规格数: {total_specs} 个")
        self.logger.info(f"   • 新增缓存文件: {newly_cached} 个")
        self.logger.info(f"   • 当前总缓存: {final_cache_count} 个")
        if len(all_products) > 0:
            success_rate = success_count / len(all_products) * 100
            self.logger.info(f"   • 本次成功率: {success_rate:.1f}%")
        
        # 保存异常记录
        self._save_error_logs()
        
        return data

    def _crawl_products_serial(self, leaves: List[Dict]) -> Dict[str, List[str]]:
        """串行处理叶节点产品链接（原始方法）"""
        leaf_products = {}
        
        for i, leaf in enumerate(leaves, 1):
            self.logger.info(f"[{i}/{len(leaves)}] 处理叶节点: {leaf['code']}")
            try:
                products = self._crawl_products_for_leaf(leaf)
                leaf_products[leaf['code']] = products
                self.progress_tracker.update_task("产品链接扩展", success=True)
                
                # 显示成功信息（包含URL）
                retry_info = ""
                if leaf.get('is_retry'):
                    retry_info = f" (重试{leaf.get('previous_tries', 0)}次)"
                
                if products:
                    self.logger.info(f"✅ 叶节点 {leaf['code']} 产品数: {len(products)}{retry_info}")
                    self.logger.info(f"   地址: {leaf['url']}")
                    
                    # 成功获取产品，标记为成功修复（下次运行时自动不会重试）
                    if leaf.get('is_retry'):
                        prev_tries = leaf.get('previous_tries', 0)
                        self.logger.info(f"🎉 成功修复！叶节点 {leaf['code']} (之前失败 {prev_tries} 次)")
                else:
                    self.logger.warning(f"⚠️  叶节点 {leaf['code']} 无产品{retry_info}")
                    self.logger.warning(f"   地址: {leaf['url']}")
                    
                    # 记录零产品情况到错误日志
                    self._record_error('products', {
                        'error_type': 'zero_products',
                        'leaf_code': leaf['code'],
                        'leaf_name': leaf.get('name', ''),
                        'leaf_url': leaf['url'],
                        'product_count': 0,
                        'note': '页面访问正常但未找到产品'
                    })
                    
                    # 失败信息已经通过 _record_error 记录到错误日志中
                    
            except Exception as e:
                retry_info = ""
                if leaf.get('is_retry'):
                    retry_info = f" (重试{leaf.get('previous_tries', 0)}次)"
                
                self.logger.error(f"叶节点 {leaf['code']} 处理失败: {e}{retry_info}")
                self.logger.error(f"   地址: {leaf['url']}")
                
                # 记录产品链接爬取失败到错误日志
                self._record_error('products', {
                    'error_type': 'product_extraction_failed',
                    'leaf_code': leaf['code'],
                    'leaf_name': leaf.get('name', ''),
                    'leaf_url': leaf['url'],
                    'exception': str(e),
                    'exception_type': type(e).__name__
                })
                
                # 失败信息已经通过 _record_error 记录到错误日志中
                
                leaf_products[leaf['code']] = []
                self.progress_tracker.update_task("产品链接扩展", success=False)
        
        return leaf_products

    def _crawl_products_parallel(self, leaves: List[Dict], max_processes: int = None) -> Dict[str, List[str]]:
        """并行处理叶节点产品链接（进程池模式）"""
        import multiprocessing as mp
        from multiprocessing import Pool
        import time
        
        # 动态确定进程数
        if max_processes is None:
            # 根据 --workers 参数动态调整并发数
            # 对于产品链接抓取，使用一半的 workers（因为每个进程会启动 Playwright）
            # 但至少保证有 2 个进程，最多不超过叶节点数量
            max_processes = min(
                max(self.max_workers // 2, 2),  # 至少2个进程，最多是 workers 的一半
                len(leaves),  # 不超过叶节点数量
                min(self.max_workers, 16)  # 不超过 workers 设置，但也不超过 16（系统资源考虑）
            )
        else:
            # 使用调用者指定的进程数，但仍要遵守合理限制
            max_processes = min(max_processes, len(leaves), 16)
        
        # 准备参数：为每个叶节点创建独立的参数包
        leaf_args = []
        for leaf in leaves:
            # 传递缓存检查需要的参数
            leaf_args.append({
                'leaf': leaf,
                'cache_dir': str(self.products_cache_dir),
                'cache_ttl_hours': self.cache_ttl[CacheLevel.PRODUCTS],
                'debug_mode': self.debug_mode
            })
        
        leaf_products = {}
        errors = []
        
        try:
            with Pool(processes=max_processes) as pool:
                self.logger.info(f"🚀 启动 {max_processes} 个进程处理 {len(leaves)} 个叶节点...")
                
                # 提交所有任务
                results = pool.map(_crawl_single_leaf_product_worker, leaf_args)
                
                # 处理结果
                for result in results:
                    leaf_code = result['leaf_code']
                    products = result['products']
                    error_info = result.get('error_info')
                    
                    leaf_products[leaf_code] = products
                    
                    # 记录错误信息
                    if error_info:
                        errors.append(error_info)
                        self.progress_tracker.update_task("产品链接扩展", success=False)
                    else:
                        self.progress_tracker.update_task("产品链接扩展", success=True)
                    
                    # 显示结果
                    if products:
                        self.logger.info(f"✅ 叶节点 {leaf_code} 产品数: {len(products)}")
                    else:
                        self.logger.warning(f"⚠️ 叶节点 {leaf_code} 无产品")
                        
        except Exception as e:
            self.logger.error(f"❌ 并行处理失败，回退到串行模式: {e}")
            return self._crawl_products_serial(leaves)
        
        # 批量记录错误
        for error_info in errors:
            self._record_error('products', error_info)
        
        self.logger.info(f"🏁 并行处理完成: {len(leaf_products)} 个叶节点, {len(errors)} 个错误")
        
        return leaf_products

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
                
                # 检查缓存内容是否有效（非空）
                if products and len(products) > 0:
                    products = self._ensure_absolute_urls(products)
                    self.logger.info(f"📦 使用有效缓存: {code} ({len(products)} 个产品)")
                    return products
                else:
                    self.logger.warning(f"⚠️ 发现空缓存: {code}，将重新爬取")
        
        # 爬取新数据
        self.logger.info(f"🌐 爬取产品: {code}")
        self.logger.info(f"🔗 叶节点URL: {leaf['url']}")
        try:
            # 使用新的v2接口，包含进度信息
            products, progress_info = self.products_crawler.collect_all_product_links(leaf['url'])
            products = self._ensure_absolute_urls(products)
            # 记录进度信息到日志
            target_count = progress_info.get('target_count_on_page', 0)
            if target_count > 0:
                self.logger.info(f"📊 抓取完成度: {progress_info['progress_percentage']}% ({progress_info['extracted_count']}/{target_count})")
            
            # 记录空产品列表的情况（没有异常但结果为空）
            if not products:
                self._record_error('products', {
                    'error_type': 'zero_products_no_exception',
                    'leaf_code': code,
                    'leaf_name': leaf.get('name', ''),
                    'leaf_url': leaf['url'],
                    'product_count': 0,
                    'note': '爬取完成但返回空产品列表'
                })
            
            # 保存缓存（确保URL是绝对路径）
            products_to_save = [link if link.startswith("http") else f"https://www.traceparts.cn{link}" for link in products]
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(products_to_save, f, ensure_ascii=False, indent=2)
            return products
        except Exception as e:
            self.logger.error(f"❌ 失败: {code} - {e}")
            
            # 记录爬取异常
            self._record_error('products', {
                'error_type': 'product_extraction_exception',
                'leaf_code': code,
                'leaf_name': leaf.get('name', ''),
                'leaf_url': leaf['url'],
                'exception': str(e),
                'exception_type': type(e).__name__,
                'note': '产品链接爬取过程中发生异常'
            })
            
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
        
        # 更新树（如果存在root）
        if 'root' in data:
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
        
        # 更新树（如果存在root）
        if 'root' in data:
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
    
    def run_progressive_cache(self, target_level: CacheLevel = CacheLevel.SPECIFICATIONS, force_refresh: bool = False, retry_failed_only: bool = False):
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
            
            root, leaves = self.classification_crawler.crawl_full_tree_enhanced()
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
        elif current_level.value >= CacheLevel.PRODUCTS.value and target_level.value >= CacheLevel.PRODUCTS.value:
            # 即使已经到达PRODUCTS级别，也要检查是否有失败的产品链接需要重试
            failed_products_db = self._load_failed_products_from_error_logs(max_retry_times=3)
            if failed_products_db:
                self.logger.info("\n[阶段 2/3] 重新处理失败的产品链接")
                self.logger.info("-" * 50)
                self.logger.info(f"🔄 检测到 {len(failed_products_db)} 个失败的叶节点，需要重新爬取产品链接")
                
                data = self.extend_to_products(data)
                self.save_cache(data, CacheLevel.PRODUCTS)
                
                if target_level == CacheLevel.PRODUCTS:
                    self.logger.info("\n✅ 已达到目标缓存级别")
                    return data
        
        if current_level.value < CacheLevel.SPECIFICATIONS.value and target_level.value >= CacheLevel.SPECIFICATIONS.value:
            self.logger.info("\n[阶段 3/3] 扩展产品规格缓存")
            self.logger.info("-" * 50)
            
            data = self.extend_to_specifications(data, retry_failed_only=retry_failed_only)
            self.save_cache(data, CacheLevel.SPECIFICATIONS)
            
            self.logger.info("\n✅ 已达到目标缓存级别")
        
        return data

    # === 失败规格增量记录 ===
    def _load_failed_specs(self) -> Dict[str, Dict]:
        """加载失败规格记录，返回 url->record 字典"""
        failed = {}
        if self.failed_specs_file.exists():
            with open(self.failed_specs_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        rec = json.loads(line.strip())
                        failed[rec.get('url')] = rec
                    except:
                        continue
        return failed

    def _append_failed_spec(self, record: Dict):
        """线程安全地更新失败记录（确保唯一性）"""
        with self.failed_lock:
            # 读取现有记录
            existing_records = {}
            if self.failed_specs_file.exists():
                try:
                    with open(self.failed_specs_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                existing_record = json.loads(line.strip())
                                url = existing_record.get('url')
                                if url:
                                    existing_records[url] = existing_record
                            except:
                                continue
                except Exception as e:
                    self.logger.warning(f"读取失败记录文件失败: {e}")
            
            # 更新或添加新记录
            url = record.get('url')
            if url:
                existing_records[url] = record
            
            # 重写整个文件以确保唯一性
            try:
                with open(self.failed_specs_file, 'w', encoding='utf-8') as f:
                    for record_data in existing_records.values():
                        f.write(json.dumps(record_data, ensure_ascii=False) + "\n")
            except Exception as e:
                self.logger.error(f"写入失败记录文件失败: {e}")
                # 如果写入失败，尝试追加模式作为备份
                try:
                    with open(self.failed_specs_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                except:
                    pass
    
    def _is_product_cached(self, product_url: str, leaf_code: str = None) -> bool:
        """检查产品规格是否已经缓存"""
        try:
            import hashlib
            
            # 如果没有leaf_code，尝试从URL推断或使用unknown
            if not leaf_code:
                leaf_code = 'unknown'
            
            # 生成缓存文件路径
            url_hash = hashlib.md5(product_url.encode()).hexdigest()[:12]
            base_name = f"{leaf_code}_{url_hash}"
            
            # 检查多种格式的缓存文件（优先检查新格式）
            cache_files_to_check = [
                self.specs_cache_dir / f"{base_name}_complete.json",  # 新格式：完整JSON
                self.specs_cache_dir / f"{base_name}.json",           # 原始格式：兼容性
            ]
            
            for cache_file in cache_files_to_check:
                if cache_file.exists():
                    file_size = cache_file.stat().st_size
                    if file_size > 10:  # 至少10字节，避免空文件
                        # 快速验证是否为有效JSON
                        try:
                            with open(cache_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                
                                # 检查是否有实际规格数据
                                if cache_file.name.endswith('_complete.json'):
                                    # 新格式：检查 product_specifications 字段
                                    specs = data.get('product_specifications', [])
                                    if isinstance(specs, list) and len(specs) > 0:
                                        self.logger.debug(f"✅ 找到新格式缓存: {cache_file.name} ({len(specs)} specs)")
                                        return True
                                else:
                                    # 原始格式：直接检查数据
                                    if isinstance(data, list) and len(data) > 0:
                                        self.logger.debug(f"✅ 找到原格式缓存: {cache_file.name} ({len(data)} specs)")
                                        return True
                        except:
                            # 如果文件损坏，认为未缓存
                            self.logger.debug(f"⚠️ 缓存文件损坏，将重新爬取: {cache_file}")
                            continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"检查缓存状态失败: {e}")
            return False
    
    def _remove_from_failed_specs(self, product_url: str):
        """从失败记录中移除成功的产品"""
        try:
            if not self.failed_specs_file.exists():
                return
            
            # 读取所有记录
            failed_records = []
            with open(self.failed_specs_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        # 只保留不是当前URL的记录
                        if record.get('url') != product_url:
                            failed_records.append(record)
                    except:
                        continue
            
            # 重写文件
            with self.failed_lock:
                with open(self.failed_specs_file, 'w', encoding='utf-8') as f:
                    for record in failed_records:
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        
            self.logger.debug(f"✅ 已从失败记录中移除: {product_url}")
            
        except Exception as e:
            self.logger.warning(f"移除失败记录时出错: {e}")
    
    def _get_cached_specs_count(self) -> int:
        """获取已缓存的规格文件数量（按产品计算，不按文件格式）"""
        try:
            if not self.specs_cache_dir.exists():
                return 0
            
            # 统计唯一的产品（通过base_name去重）
            base_names = set()
            
            # 检查完整格式文件
            for complete_file in self.specs_cache_dir.glob("*_complete.json"):
                base_name = complete_file.name.replace('_complete.json', '')
                base_names.add(base_name)
            
            # 检查原始格式文件（排除已有完整格式的）
            for json_file in self.specs_cache_dir.glob("*.json"):
                if not json_file.name.endswith(('_complete.json', '_list.json')):
                    base_name = json_file.name.replace('.json', '')
                    base_names.add(base_name)
            
            return len(base_names)
        except:
            return 0
    
    def _cleanup_duplicate_failed_specs(self):
        """清理重复的失败记录（初始化时执行）"""
        if not self.failed_specs_file.exists():
            return
        
        try:
            # 读取所有记录，按URL去重
            unique_records = {}
            total_lines = 0
            
            with open(self.failed_specs_file, 'r', encoding='utf-8') as f:
                for line in f:
                    total_lines += 1
                    try:
                        record = json.loads(line.strip())
                        url = record.get('url')
                        if url:
                            # 如果已存在，比较时间戳，保留最新的
                            if url in unique_records:
                                existing_ts = unique_records[url].get('ts', '')
                                new_ts = record.get('ts', '')
                                if new_ts > existing_ts:
                                    unique_records[url] = record
                            else:
                                unique_records[url] = record
                    except:
                        continue
            
            # 如果有重复，重写文件
            if len(unique_records) < total_lines:
                duplicate_count = total_lines - len(unique_records)
                self.logger.info(f"🧹 清理失败记录重复项: {duplicate_count} 个，保留 {len(unique_records)} 个唯一记录")
                
                # 备份原文件
                backup_file = self.failed_specs_file.with_suffix('.jsonl.backup')
                if backup_file.exists():
                    backup_file.unlink()  # 删除旧备份
                self.failed_specs_file.rename(backup_file)
                
                # 重写去重后的记录
                with open(self.failed_specs_file, 'w', encoding='utf-8') as f:
                    for record in unique_records.values():
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        
        except Exception as e:
            self.logger.warning(f"清理重复失败记录时出错: {e}")
    
    def close(self):
        """关闭缓存管理器，清理资源"""
        self.logger.info("🛑 关闭缓存管理器...")
        
        # 清理规格爬取器资源（如果需要）
        # 原版规格爬取器不需要特殊关闭，这里预留给将来扩展
        
        self.logger.info("✅ 缓存管理器已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ----- New Method for Single URL Testing -----
    def run_single_url_test(self, test_url: str, target_level: CacheLevel, force_refresh: bool = False) -> Dict[str, Any]:
        """Process a single URL through the caching stages for testing purposes."""
        self.logger.info(f"🧪 [CacheManager] Running single URL test for: {test_url} (Target: {target_level.name}, Refresh: {force_refresh})")
        
        tp_code = self._extract_tp_code_from_url(test_url)
        if not tp_code:
            self.logger.error(f"❌ [CacheManager] Could not extract TP_CODE from test URL: {test_url}")
            return {"error": "Could not extract TP_CODE", "url": test_url, "tp_code": None}
        
        node_name = f"TestNode-{tp_code}"
        node = {
            'url': test_url,
            'name': node_name,
            'code': tp_code,
            'level': 4, 
            'children': [],
            'is_leaf': None, 
            'is_potential_leaf': True, 
            'products_on_page': 0,
            # Construct paths similar to how they would be for actual caching, though we might not save all steps
            'product_links_file': self.products_cache_dir / f"{tp_code}_products.json",
            'specification_dir': self.specs_cache_dir / tp_code
        }
        self.logger.info(f"🧬 [CacheManager] Created test node: Code={tp_code}, Name={node_name}")

        test_results = {
            "url": test_url,
            "tp_code": tp_code,
            "node_name": node_name,
            "stages_processed": [],
            "is_leaf_node": None,
            "target_product_count": 0,
            "product_links_count": 0,
            "product_links_data": None, # To store actual links if fetched
            "specification_summary": None
        }

        # Stage 1: Classification (Leaf Node Verification)
        self.logger.info(f"➡️ [CacheManager] Stage 1: Verifying leaf status for {tp_code}")
        self.classification_crawler.debug_mode = self.debug_mode
        is_leaf_status, target_count, details_dict = self.classification_crawler._check_single_leaf_node(node)
        node['is_leaf'] = is_leaf_status
        node['products_on_page'] = target_count # This is the target_count from classification
        test_results["is_leaf_node"] = is_leaf_status
        test_results["target_product_count"] = target_count
        test_results["stages_processed"].append("classification_check")
        self.logger.info(f"   📄 Leaf status: {is_leaf_status}, Target products (from classification): {target_count}")

        if not is_leaf_status:
            self.logger.info(f"🛑 [CacheManager] Node {tp_code} is not a leaf. Test processing for this URL ends here.")
            return test_results

        # Stage 2: Product Links
        fetched_links_data = None
        if target_level.value >= CacheLevel.PRODUCTS.value:
            self.logger.info(f"➡️ [CacheManager] Stage 2: Fetching product links for {tp_code} (Force refresh: {force_refresh})")
            try:
                # The method in ultimate_products_v2.py is collect_all_product_links(self, leaf_url: str, tp_code: str, ...)
                # It does not take current_target_count; it determines target_count internally.
                fetched_links_data_tuple = self.products_crawler.collect_all_product_links(
                    leaf_url=node['url'], 
                    tp_code=node['code']
                    # Removed current_target_count and force_refresh from this direct call
                    # force_refresh for the product links stage in a single test would imply that
                    # collect_all_product_links itself should not use any of its own potential caching,
                    # which is usually the case as it fetches live data.
                )
                
                # collect_all_product_links returns a tuple: (links_list, progress_info_dict)
                if fetched_links_data_tuple and isinstance(fetched_links_data_tuple, tuple) and len(fetched_links_data_tuple) == 2:
                    links_list, progress_info_dict = fetched_links_data_tuple
                    fetched_links_data = {
                        "leaf_url": node['url'],
                        "tp_code": node['code'],
                        "links": links_list,
                        "progress_info": progress_info_dict,
                        "timestamp": progress_info_dict.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
                    }
                    test_results["product_links_count"] = len(links_list)
                    test_results["product_links_data"] = fetched_links_data
                    
                    if "target_count_on_page" in progress_info_dict:
                        # Update the overall test_results target_product_count if product crawler found one
                        # This might differ from the one found by classification_crawler if logic varies
                        test_results["target_product_count"] = progress_info_dict["target_count_on_page"]
                        self.logger.info(f"   🎯 Target products (from product links crawler): {progress_info_dict['target_count_on_page']}")

                    self.logger.info(f"   🔗 Product links fetched: {test_results['product_links_count']}")
                else:
                    self.logger.warning(f"   ⚠️ No product links fetched for {tp_code} or data was empty/malformed. Response from crawler: {fetched_links_data_tuple}")
                    fetched_links_data = None # Ensure it's None if fetching failed

            except Exception as e_prod:
                self.logger.error(f"   ❌ Error fetching product links for {tp_code}: {e_prod}", exc_info=self.debug_mode)
            test_results["stages_processed"].append("product_links_fetch")
        else:
            self.logger.info(f"⚪️ [CacheManager] Stage 2: Product links (skipped by target_level: {target_level.name})")

        # Stage 3: Specifications
        if target_level.value >= CacheLevel.SPECIFICATIONS.value:
            if fetched_links_data and fetched_links_data.get('links'):
                product_links_for_specs = [
                    f"https://www.traceparts.cn{link}" if link.startswith('/') else link
                    for link in fetched_links_data['links']
                ]
                self.logger.info(f"➡️ [CacheManager] Stage 3: Fetching specifications for {tp_code} (Products: {len(product_links_for_specs)}, Force refresh: {force_refresh})")
                try:
                    # Changed to use extract_batch_specifications
                    # The method returns a dict like: {'results': [], 'summary': {}}
                    specs_data_dict = self.specifications_crawler.extract_batch_specifications(
                        product_urls=product_links_for_specs
                        # force_refresh is not directly passed; it's handled by --no-cache in Makefile for the crawler
                    )
                    
                    # Store the summary or a relevant part of specs_data_dict
                    test_results["specification_summary"] = {
                        "processed_count": len(product_links_for_specs),
                        "successful_count": specs_data_dict.get('summary', {}).get('success_cnt', 0),
                        "total_specs_found": specs_data_dict.get('summary', {}).get('total_specs', 0),
                        # Optionally, store all detailed results if small enough or needed for debug
                        # "details": specs_data_dict.get('results', []) 
                    }
                    test_results["stages_processed"].append("specifications_fetch")
                    self.logger.info(f"   🔩 Specifications fetched for {tp_code}: {test_results['specification_summary']}")
                except Exception as e:
                    self.logger.error(f"❌ Error fetching specifications for {tp_code}: {e}", exc_info=self.debug_mode)
                    test_results["specification_summary"] = {"error": str(e)}
            else:
                self.logger.info(f"⚪️ [CacheManager] Stage 3: Specifications (skipped, no product links found for {tp_code})")
        else:
             self.logger.info(f"⚪️ [CacheManager] Stage 3: Specifications (skipped by target_level: {target_level.name})")

        self.logger.info(f"🏁 [CacheManager] Single URL test finished for {tp_code}. Results: {test_results}")
        return test_results

    def _extract_tp_code_from_url(self, url: str) -> Optional[str]:
        """Extracts the TP code from a URL's CatalogPath query parameter."""
        from urllib.parse import urlparse, parse_qs
        try:
            qs_part = urlparse(url).query
            params = parse_qs(qs_part)
            cp = params.get('CatalogPath', [''])[0]
            if cp.startswith('TRACEPARTS:'):
                cp = cp.split(':',1)[1]
            return cp if cp else None
        except Exception as e:
            self.logger.error(f"Error extracting TP_CODE from URL '{url}': {e}")
            return None

    def _get_cache_path(self, tp_code: str, level: CacheLevel, is_dir: bool = False) -> Path:
        """Returns the cache path for a given TP code and level."""
        # Implementation of _get_cache_path method
        pass

    def _classification_crawler(self):
        """Returns the classification crawler."""
        # Implementation of _classification_crawler method
        pass

    def _product_links_crawler(self):
        """Returns the product links crawler."""
        # Implementation of _product_links_crawler method
        pass

    def _spec_crawler(self):
        """Returns the specification crawler."""
        # Implementation of _spec_crawler method
        pass

    def _debug_mode(self):
        """Returns the debug mode."""
        # Implementation of _debug_mode method
        pass

    def _cache_base_dir(self):
        """Returns the cache base directory."""
        # Implementation of _cache_base_dir method
        pass

    def _classification_crawler(self):
        """Returns the classification crawler."""
        # Implementation of _classification_crawler method
        pass

    def _product_links_crawler(self):
        """Returns the product links crawler."""
        # Implementation of _product_links_crawler method
        pass

    def _spec_crawler(self):
        """Returns the specification crawler."""
        # Implementation of _spec_crawler method
        pass

    def _debug_mode(self):
        """Returns the debug mode."""
        # Implementation of _debug_mode method
        pass

    def _cache_base_dir(self):
        """Returns the cache base directory."""
        # Implementation of _cache_base_dir method
        pass 

    def _ensure_absolute_urls(self, links, base="https://www.traceparts.cn"):
        return [link if link.startswith("http") else base + link for link in links]
    
    # === 失败产品增量记录管理（使用现有错误日志系统）===
    def _load_failed_products_from_error_logs(self, max_retry_times: int = 3) -> Dict[str, Dict]:
        """从错误日志中加载失败产品记录，自动验证和剔除已修复的记录"""
        failed_products = {}
        
        if not self.error_logs_dir.exists():
            return failed_products
        
        # 找到最新的错误日志文件
        error_log_files = list(self.error_logs_dir.glob('error_log_v*.json'))
        if not error_log_files:
            return failed_products
        
        # 按文件名排序，取最新的
        latest_error_log = sorted(error_log_files, key=lambda x: x.name)[-1]
        
        try:
            with open(latest_error_log, 'r', encoding='utf-8') as f:
                error_data = json.load(f)
            
            product_errors = error_data.get('details', {}).get('products', [])
            
            # 统计每个叶节点的失败次数（防止死循环）
            failure_counts = {}
            for error in product_errors:
                leaf_code = error.get('leaf_code')
                if leaf_code:
                    failure_counts[leaf_code] = failure_counts.get(leaf_code, 0) + 1
            
            # 收集可重试的失败记录
            candidate_failures = []
            for error in product_errors:
                leaf_code = error.get('leaf_code')
                error_type = error.get('error_type', '')
                
                if leaf_code and failure_counts.get(leaf_code, 0) <= max_retry_times:
                    if error_type in ['zero_products_no_exception', 'product_extraction_failed', 'zero_products']:
                        candidate_failures.append({
                            'leaf_code': leaf_code,
                            'leaf_name': error.get('leaf_name', ''),
                            'leaf_url': error.get('leaf_url', ''),
                            'error_type': error_type,
                            'tries': failure_counts[leaf_code],
                            'last_timestamp': error.get('timestamp', ''),
                            'reason': error.get('note', error.get('exception', '未知原因'))
                        })
            
            # 智能验证：并行检查失败记录是否已修复，并更新错误日志
            verified_failures = {}
            recovered_codes = []
            
            if candidate_failures:
                self.logger.info(f"🔍 并行智能验证失败记录...")
                sample_size = min(20, len(candidate_failures))  # 增加到前20个，并行处理速度快
                
                # 并行验证缓存文件
                verification_results = self._parallel_verify_cache_files(candidate_failures[:sample_size])
                
                for failure, (is_recovered, product_count) in zip(candidate_failures[:sample_size], verification_results):
                    leaf_code = failure['leaf_code']
                    
                    if is_recovered:
                        self.logger.info(f"✅ 检测到已修复: {leaf_code} (现有 {product_count} 个产品)")
                        recovered_codes.append(leaf_code)
                    else:
                        # 仍然是失败状态
                        verified_failures[leaf_code] = failure
                
                # 对于未验证的失败记录，直接加入（避免验证时间过长）
                for failure in candidate_failures[sample_size:]:
                    verified_failures[failure['leaf_code']] = failure
                
                # 如果有已修复的记录，更新错误日志文件
                if recovered_codes:
                    self._update_error_log_file(latest_error_log, error_data, recovered_codes)
            
            failed_products = verified_failures
            
            self.logger.info(f"📊 从 {latest_error_log.name} 智能加载失败产品记录")
            self.logger.info(f"   • 总错误记录: {len(product_errors)} 个")
            self.logger.info(f"   • 候选重试: {len(candidate_failures)} 个")
            self.logger.info(f"   • 并行验证: {min(20, len(candidate_failures))} 个")
            self.logger.info(f"   • 自动剔除: {len(recovered_codes)} 个")
            self.logger.info(f"   • 确认失败: {len(failed_products)} 个")
            self.logger.info(f"   • 超限跳过: {len([k for k, v in failure_counts.items() if v > max_retry_times])} 个")
            
        except Exception as e:
            self.logger.error(f"读取错误日志失败: {e}")
        
        return failed_products

    def _is_leaf_in_current_error_batch(self, leaf_code: str) -> bool:
        """检查叶节点是否在当前批次的错误记录中（避免重复记录）"""
        for error in self.error_records.get('products', []):
            if error.get('leaf_code') == leaf_code:
                return True
        return False
    
    def _verify_single_cache_file(self, failure_record: Dict) -> Tuple[bool, int]:
        """验证单个缓存文件是否已修复，返回(是否已修复, 产品数量)"""
        leaf_code = failure_record['leaf_code']
        
        try:
            cache_file = self.products_cache_dir / f"{leaf_code}.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_products = json.load(f)
                
                if cached_products and len(cached_products) > 0:
                    return True, len(cached_products)  # 已修复
            
            return False, 0  # 仍然失败
            
        except Exception as e:
            # 缓存文件有问题，继续当作失败处理
            return False, 0
    
    def _parallel_verify_cache_files(self, failure_records: List[Dict]) -> List[Tuple[bool, int]]:
        """并行验证多个缓存文件是否已修复"""
        if not failure_records:
            return []
        
        # 使用线程池并行检查缓存文件（IO密集型任务，适合用线程）
        max_workers = min(8, len(failure_records))  # 最多8个线程，避免过多IO竞争
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有验证任务
            future_to_record = {
                executor.submit(self._verify_single_cache_file, record): record 
                for record in failure_records
            }
            
            # 收集结果，保持原始顺序
            results = []
            for record in failure_records:
                # 找到对应的future
                future = next(f for f, r in future_to_record.items() if r == record)
                try:
                    result = future.result(timeout=5)  # 5秒超时
                    results.append(result)
                except Exception as e:
                    # 验证失败，当作仍然失败处理
                    self.logger.debug(f"验证缓存文件失败 {record['leaf_code']}: {e}")
                    results.append((False, 0))
        
        return results

    def _update_error_log_file(self, error_log_path: Path, error_data: Dict, recovered_codes: List[str]):
        """更新错误日志文件，删除已修复的记录并更新统计"""
        try:
            self.logger.info(f"📝 更新错误日志文件，剔除 {len(recovered_codes)} 个已修复记录...")
            
            # 获取原始产品错误列表
            original_product_errors = error_data.get('details', {}).get('products', [])
            
            # 过滤掉已修复的记录
            updated_product_errors = [
                error for error in original_product_errors 
                if error.get('leaf_code') not in recovered_codes
            ]
            
            # 更新error_data
            updated_error_data = error_data.copy()
            updated_error_data['details']['products'] = updated_product_errors
            
            # 更新summary统计
            old_summary = updated_error_data.get('summary', {})
            new_summary = old_summary.copy()
            new_summary.update({
                'total_product_errors': len(updated_product_errors),
                'auto_cleanup_info': {
                    'last_cleanup_at': datetime.now().isoformat(),
                    'recovered_count': len(recovered_codes),
                    'recovered_codes': recovered_codes,
                    'original_count': len(original_product_errors)
                }
            })
            updated_error_data['summary'] = new_summary
            
            # 备份原文件
            backup_path = error_log_path.with_suffix('.json.bak')
            if backup_path.exists():
                backup_path.unlink()
            error_log_path.rename(backup_path)
            
            # 保存更新后的文件
            with open(error_log_path, 'w', encoding='utf-8') as f:
                json.dump(updated_error_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 错误日志已更新: {error_log_path.name}")
            self.logger.info(f"   • 原始错误: {len(original_product_errors)} 个")
            self.logger.info(f"   • 已修复剔除: {len(recovered_codes)} 个")
            self.logger.info(f"   • 剩余错误: {len(updated_product_errors)} 个")
            self.logger.info(f"   • 备份文件: {backup_path.name}")
            
        except Exception as e:
            self.logger.error(f"❌ 更新错误日志文件失败: {e}")
            # 如果更新失败，尝试恢复备份
            try:
                if backup_path.exists():
                    backup_path.rename(error_log_path)
                    self.logger.info("🔄 已恢复原始错误日志文件")
            except Exception as restore_e:
                self.logger.error(f"❌ 恢复备份也失败: {restore_e}")