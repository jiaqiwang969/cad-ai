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
        
        # 初始化爬取器
        self.classification_crawler = OptimizedClassificationCrawler()
        self.products_crawler = UltimateProductLinksCrawler()
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
        """记录错误信息"""
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'version': f'v{self.timestamp}',
            **error_info
        }
        
        if error_type in self.error_records:
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
                        
                        # 记录零产品情况
                        self._record_error('products', {
                            'error_type': 'zero_products',
                            'leaf_code': leaf['code'],
                            'leaf_name': leaf.get('name', ''),
                            'leaf_url': leaf['url'],
                            'product_count': 0,
                            'note': '页面访问正常但未找到产品'
                        })
                        
                except Exception as e:
                    self.logger.error(f"叶节点 {leaf['code']} 处理失败: {e}")
                    self.logger.error(f"   地址: {leaf['url']}")
                    
                    # 记录产品链接爬取失败
                    self._record_error('products', {
                        'error_type': 'product_extraction_failed',
                        'leaf_code': leaf['code'],
                        'leaf_name': leaf.get('name', ''),
                        'leaf_url': leaf['url'],
                        'exception': str(e),
                        'exception_type': type(e).__name__
                    })
                    
                    leaf_products[leaf['code']] = []
                    self.progress_tracker.update_task("产品链接扩展", success=False)
        
        # 更新数据结构
        self._update_tree_with_products(data, leaf_products)
        
        # 统计
        total_products = sum(len(products) for products in leaf_products.values())
        self.logger.info(f"\n✅ 产品链接扩展完成:")
        self.logger.info(f"   • 处理叶节点: {len(leaves)} 个")
        self.logger.info(f"   • 总产品数: {total_products} 个")
        
        # 保存异常记录（如果有的话）
        if self.error_records['products']:
            self._save_error_logs()
        
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
        
        # 使用优化的线程数配置
        max_workers = min(len(all_products), 12)
        
        # 提取所有产品URL
        product_urls = [p['product_url'] if isinstance(p, dict) else p for p in all_products]
        
        # 批量爬取
        batch_result = self.specifications_crawler.extract_batch_specifications(
            product_urls, 
            max_workers=max_workers
        )
        
        # 处理结果
        product_specs = {}
        success_count = 0
        total_specs = 0
        
        for result in batch_result.get('results', []):
            product_url = result['product_url']
            specs = result.get('specifications', [])
            product_specs[product_url] = specs
            
            if result.get('success', False):
                success_count += 1
                total_specs += len(specs)
                
                # 记录零规格情况（成功访问但无规格）
                if len(specs) == 0:
                    # 找到对应的产品信息
                    product_info = next((p for p in all_products if (p['product_url'] if isinstance(p, dict) else p) == product_url), None)
                    
                    self._record_error('specifications', {
                        'error_type': 'zero_specifications',
                        'product_url': product_url,
                        'leaf_code': product_info.get('leaf_code', 'unknown') if isinstance(product_info, dict) else 'unknown',
                        'spec_count': 0,
                        'success': True,
                        'note': '页面访问成功但未提取到产品规格'
                    })
                    
                # 记录规格数量较少的情况（可能的问题）
                elif len(specs) == 1:
                    product_info = next((p for p in all_products if (p['product_url'] if isinstance(p, dict) else p) == product_url), None)
                    
                    self._record_error('specifications', {
                        'error_type': 'low_specification_count',
                        'product_url': product_url,
                        'leaf_code': product_info.get('leaf_code', 'unknown') if isinstance(product_info, dict) else 'unknown',
                        'spec_count': len(specs),
                        'success': True,
                        'note': '规格数量较少，可能存在提取问题',
                        'specifications': specs  # 包含具体的规格内容用于调试
                    })
            else:
                # 记录完全失败的情况
                product_info = next((p for p in all_products if (p['product_url'] if isinstance(p, dict) else p) == product_url), None)
                error_msg = result.get('error', '未知错误')
                
                self.logger.warning(f"⚠️ 产品规格爬取失败: {product_url}")
                self.logger.warning(f"   错误: {error_msg}")
                
                self._record_error('specifications', {
                    'error_type': 'specification_extraction_failed',
                    'product_url': product_url,
                    'leaf_code': product_info.get('leaf_code', 'unknown') if isinstance(product_info, dict) else 'unknown',
                    'spec_count': 0,
                    'success': False,
                    'exception': error_msg,
                    'note': '产品规格爬取完全失败'
                })
        
        # 更新数据结构
        self._update_tree_with_specifications(data, product_specs)
        
        # 统计
        self.logger.info(f"\n✅ 产品规格扩展完成:")
        self.logger.info(f"   • 处理产品: {len(all_products)} 个")
        self.logger.info(f"   • 成功爬取: {success_count} 个")
        self.logger.info(f"   • 总规格数: {total_specs} 个")
        
        # 保存异常记录
        self._save_error_logs()
        
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
            
            # 保存缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
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