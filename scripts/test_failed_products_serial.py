#!/usr/bin/env python3
"""
测试串行模式处理失败产品URL
验证是否是并行处理导致的问题
"""

import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.pipelines.cache_manager import CacheManager

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    return logging.getLogger(__name__)

def get_latest_error_log() -> Path:
    """获取最新的错误日志文件"""
    error_logs_dir = BASE_DIR / "results" / "cache" / "error_logs"
    if not error_logs_dir.exists():
        raise FileNotFoundError("错误日志目录不存在")
    
    error_files = list(error_logs_dir.glob("error_log_v*.json"))
    if not error_files:
        raise FileNotFoundError("未找到错误日志文件")
    
    return sorted(error_files, key=lambda x: x.name)[-1]

def extract_failed_leaves(error_log_path: Path, max_test_count: int = 5) -> List[Dict[str, Any]]:
    """从错误日志中提取失败的叶节点"""
    try:
        with open(error_log_path, 'r', encoding='utf-8') as f:
            error_data = json.load(f)
        
        product_errors = error_data.get('details', {}).get('products', [])
        failed_leaves = []
        
        for error in product_errors:
            leaf_code = error.get('leaf_code')
            leaf_url = error.get('leaf_url')
            error_type = error.get('error_type', '')
            
            if leaf_code and leaf_url and error_type in ['zero_products', 'zero_products_no_exception', 'product_extraction_failed']:
                failed_leaves.append({
                    'code': leaf_code,
                    'url': leaf_url,
                    'name': error.get('leaf_name', ''),
                    'error_type': error_type,
                    'is_leaf': True
                })
        
        # 去重（按leaf_code）
        unique_leaves = {}
        for item in failed_leaves:
            unique_leaves[item['code']] = item
        
        result = list(unique_leaves.values())[:max_test_count]
        return result
        
    except Exception as e:
        logging.error(f"读取错误日志失败: {e}")
        return []

def main():
    logger = setup_logging()
    logger.info("🚀 测试串行模式处理失败产品URL")
    
    try:
        # 获取最新错误日志
        error_log_path = get_latest_error_log()
        logger.info(f"📁 使用错误日志: {error_log_path.name}")
        
        # 提取失败的叶节点
        failed_leaves = extract_failed_leaves(error_log_path, max_test_count=3)
        
        if not failed_leaves:
            logger.warning("⚠️ 未找到失败的叶节点")
            return
        
        logger.info(f"📋 找到 {len(failed_leaves)} 个失败的叶节点待测试")
        
        # 使用CacheManager的串行模式
        cache_manager = CacheManager(max_workers=1, debug_mode=True)  # 强制串行模式
        
        logger.info("🔄 使用串行模式处理失败的叶节点...")
        
        # 直接调用串行处理方法
        leaf_products = cache_manager._crawl_products_serial(failed_leaves)
        
        # 输出结果
        logger.info(f"\n{'='*60}")
        logger.info("📊 串行处理结果")
        logger.info(f"{'='*60}")
        
        success_count = 0
        no_products_count = 0
        
        for leaf in failed_leaves:
            leaf_code = leaf['code']
            products = leaf_products.get(leaf_code, [])
            
            if products:
                logger.info(f"✅ {leaf_code}: {len(products)} 个产品")
                success_count += 1
            else:
                logger.warning(f"⚠️ {leaf_code}: 无产品")
                no_products_count += 1
        
        logger.info(f"\n总结:")
        logger.info(f"✅ 成功: {success_count} 个")
        logger.info(f"⚠️ 无产品: {no_products_count} 个")
        
        # 如果串行模式成功了，说明问题在于并行处理
        if success_count > 0:
            logger.info("\n🎯 结论: 串行模式能够成功，问题很可能在于并行处理中的资源竞争！")
        else:
            logger.info("\n🤔 串行模式也失败，问题可能在URL本身或其他因素")
        
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 