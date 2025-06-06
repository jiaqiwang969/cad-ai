#!/usr/bin/env python3
"""
脚本：修复缓存文件中的相对URL
将所有相对路径的产品URL转换为绝对URL（添加 https://www.traceparts.cn 前缀）
"""

import json
import os
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_relative_urls_in_file(file_path: Path, base_url: str = "https://www.traceparts.cn") -> bool:
    """修复单个文件中的相对URL"""
    try:
        # 读取原文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查是否是URL列表
        if isinstance(data, list):
            # 修复URL列表
            fixed_urls = []
            changed_count = 0
            
            for url in data:
                if isinstance(url, str):
                    if url.startswith('/') and not url.startswith('http'):
                        # 相对路径，需要修复
                        fixed_url = base_url + url
                        fixed_urls.append(fixed_url)
                        changed_count += 1
                    else:
                        # 已经是绝对路径或其他格式
                        fixed_urls.append(url)
                else:
                    # 非字符串项，保持原样
                    fixed_urls.append(url)
            
            if changed_count > 0:
                # 备份原文件
                backup_path = file_path.with_suffix('.json.backup')
                if not backup_path.exists():  # 只在没有备份文件时创建备份
                    file_path.rename(backup_path)
                    logger.info(f"📋 已备份原文件: {backup_path}")
                
                # 写入修复后的数据
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(fixed_urls, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ 修复 {file_path.name}: {changed_count} 个相对URL -> 绝对URL")
                return True
            else:
                logger.debug(f"⚪️ {file_path.name}: 无需修复")
                return False
        
        # 检查是否是包含产品列表的复杂数据结构
        elif isinstance(data, dict):
            changed = False
            
            # 处理根级别的产品列表
            if 'products' in data and isinstance(data['products'], list):
                fixed_products = []
                for product in data['products']:
                    if isinstance(product, str):
                        if product.startswith('/') and not product.startswith('http'):
                            fixed_products.append(base_url + product)
                            changed = True
                        else:
                            fixed_products.append(product)
                    else:
                        fixed_products.append(product)
                
                if changed:
                    data['products'] = fixed_products
            
            # 处理leaves中的产品列表
            if 'leaves' in data and isinstance(data['leaves'], list):
                for leaf in data['leaves']:
                    if isinstance(leaf, dict) and 'products' in leaf:
                        fixed_leaf_products = []
                        leaf_changed = False
                        
                        for product in leaf['products']:
                            if isinstance(product, str):
                                if product.startswith('/') and not product.startswith('http'):
                                    fixed_leaf_products.append(base_url + product)
                                    leaf_changed = True
                                else:
                                    fixed_leaf_products.append(product)
                            elif isinstance(product, dict) and 'product_url' in product:
                                # 处理包含product_url的字典格式
                                if product['product_url'].startswith('/') and not product['product_url'].startswith('http'):
                                    product['product_url'] = base_url + product['product_url']
                                    leaf_changed = True
                                fixed_leaf_products.append(product)
                            else:
                                fixed_leaf_products.append(product)
                        
                        if leaf_changed:
                            leaf['products'] = fixed_leaf_products
                            changed = True
            
            if changed:
                # 备份并保存
                backup_path = file_path.with_suffix('.json.backup')
                if not backup_path.exists():
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    logger.info(f"📋 已备份原文件: {backup_path}")
                
                # 写入修复后的数据
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"✅ 修复复杂结构 {file_path.name}")
                return True
            else:
                logger.debug(f"⚪️ {file_path.name}: 无需修复")
                return False
        
        else:
            logger.debug(f"⚪️ {file_path.name}: 未知数据格式，跳过")
            return False
            
    except Exception as e:
        logger.error(f"❌ 处理文件失败 {file_path}: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始修复缓存文件中的相对URL")
    
    # 缓存目录路径
    cache_base = Path("results/cache")
    
    # 要处理的缓存目录
    directories_to_process = [
        cache_base / "products",      # 单个叶节点的产品链接
        cache_base,                   # 主缓存文件
    ]
    
    total_files = 0
    fixed_files = 0
    
    for cache_dir in directories_to_process:
        if not cache_dir.exists():
            logger.warning(f"⚠️ 目录不存在: {cache_dir}")
            continue
            
        logger.info(f"📁 处理目录: {cache_dir}")
        
        # 查找所有JSON文件
        json_files = list(cache_dir.glob("*.json"))
        
        for json_file in json_files:
            # 跳过备份文件
            if json_file.name.endswith('.backup'):
                continue
                
            total_files += 1
            if fix_relative_urls_in_file(json_file):
                fixed_files += 1
    
    logger.info("="*60)
    logger.info(f"🏁 修复完成!")
    logger.info(f"   📊 总文件数: {total_files}")
    logger.info(f"   🔧 修复文件数: {fixed_files}")
    logger.info(f"   ⚪️ 无需修复: {total_files - fixed_files}")
    
    if fixed_files > 0:
        logger.info("   ✅ 所有相对URL已转换为绝对URL")
        logger.info("   📋 原文件已备份为 .json.backup")
    else:
        logger.info("   ⚪️ 所有文件都是绝对URL，无需修复")

if __name__ == "__main__":
    main() 