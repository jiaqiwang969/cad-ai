#!/usr/bin/env python3
"""
测试失败产品URL的专用脚本
从错误日志中提取失败的叶节点URL，逐个进行产品链接测试
"""

import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
import argparse

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.crawler.ultimate_products_v2 import UltimateProductLinksCrawlerV2

def setup_logging(debug: bool = False):
    """配置日志"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'results/test_failed_products_{int(time.time())}.log')
        ]
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
    
    # 按文件名排序，获取最新的
    return sorted(error_files, key=lambda x: x.name)[-1]

def extract_failed_product_urls(error_log_path: Path, max_test_count: int = 5) -> List[Dict[str, Any]]:
    """从错误日志中提取失败的产品URL"""
    try:
        with open(error_log_path, 'r', encoding='utf-8') as f:
            error_data = json.load(f)
        
        product_errors = error_data.get('details', {}).get('products', [])
        failed_urls = []
        
        for error in product_errors:
            leaf_code = error.get('leaf_code')
            leaf_url = error.get('leaf_url')
            error_type = error.get('error_type', '')
            
            if leaf_code and leaf_url and error_type in ['zero_products', 'zero_products_no_exception', 'product_extraction_failed']:
                failed_urls.append({
                    'leaf_code': leaf_code,
                    'leaf_url': leaf_url,
                    'leaf_name': error.get('leaf_name', ''),
                    'error_type': error_type,
                    'reason': error.get('note', error.get('exception', '未知'))
                })
        
        # 去重（按leaf_code）
        unique_urls = {}
        for item in failed_urls:
            unique_urls[item['leaf_code']] = item
        
        result = list(unique_urls.values())[:max_test_count]
        return result
        
    except Exception as e:
        logging.error(f"读取错误日志失败: {e}")
        return []

def enhance_url(url: str) -> str:
    """给URL添加增强参数"""
    if 'PageSize=' in url:
        return url
    params = "PageSize=500&ShowAll=true&IncludeVariants=true"
    return f"{url}{'&' if '?' in url else '?'}{params}"

def test_single_url(crawler: UltimateProductLinksCrawlerV2, url_info: Dict[str, Any], logger: logging.Logger) -> Dict[str, Any]:
    """测试单个URL"""
    leaf_code = url_info['leaf_code']
    original_url = url_info['leaf_url']
    enhanced_url = enhance_url(original_url)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🧪 测试叶节点: {leaf_code}")
    logger.info(f"📝 名称: {url_info.get('leaf_name', '未知')}")
    logger.info(f"🚨 错误类型: {url_info['error_type']}")
    logger.info(f"📍 原始URL: {original_url}")
    logger.info(f"🔧 增强URL: {enhanced_url}")
    logger.info(f"{'='*80}")
    
    result = {
        'leaf_code': leaf_code,
        'original_url': original_url,
        'enhanced_url': enhanced_url,
        'error_type': url_info['error_type'],
        'test_result': 'unknown',
        'product_count': 0,
        'target_count': 0,
        'progress_percentage': 0.0,
        'completion_status': 'unknown',
        'test_duration': 0.0,
        'error_message': None
    }
    
    start_time = time.time()
    
    try:
        # 测试增强URL
        logger.info(f"🚀 开始测试增强URL...")
        product_links, progress_info = crawler.collect_all_product_links(
            leaf_url=enhanced_url,
            tp_code=leaf_code
        )
        
        end_time = time.time()
        result['test_duration'] = round(end_time - start_time, 2)
        result['product_count'] = len(product_links)
        
        if 'target_count_on_page' in progress_info:
            result['target_count'] = progress_info['target_count_on_page']
        
        if 'progress_percentage' in progress_info:
            result['progress_percentage'] = progress_info['progress_percentage']
            
        if 'completion_status' in progress_info:
            result['completion_status'] = progress_info['completion_status']
        
        # 判断测试结果
        if len(product_links) > 0:
            result['test_result'] = 'success'
            logger.info(f"✅ 测试成功！")
            logger.info(f"   产品数量: {len(product_links)}")
            logger.info(f"   目标数量: {result['target_count']}")
            logger.info(f"   完成度: {result['progress_percentage']:.1f}%")
            logger.info(f"   测试耗时: {result['test_duration']}秒")
        else:
            result['test_result'] = 'no_products'
            logger.warning(f"⚠️ 测试结果：未找到产品")
            logger.info(f"   目标数量: {result['target_count']}")
            logger.info(f"   测试耗时: {result['test_duration']}秒")
        
        # 显示进度信息
        if progress_info:
            logger.info(f"📊 详细信息: {json.dumps(progress_info, ensure_ascii=False, indent=2)}")
            
    except Exception as e:
        end_time = time.time()
        result['test_duration'] = round(end_time - start_time, 2)
        result['test_result'] = 'error'
        result['error_message'] = str(e)
        logger.error(f"❌ 测试失败: {e}")
        logger.info(f"   测试耗时: {result['test_duration']}秒")
    
    return result

def main():
    parser = argparse.ArgumentParser(description="测试失败产品URL")
    parser.add_argument('--max-test', type=int, default=5, help='最大测试URL数量')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--headless', action='store_true', default=True, help='无头模式')
    parser.add_argument('--specific-code', type=str, help='测试特定的叶节点代码')
    
    args = parser.parse_args()
    
    logger = setup_logging(args.debug)
    logger.info("🚀 启动失败产品URL测试程序")
    
    try:
        # 获取最新错误日志
        error_log_path = get_latest_error_log()
        logger.info(f"📁 使用错误日志: {error_log_path.name}")
        
        # 提取失败的URL
        failed_urls = extract_failed_product_urls(error_log_path, args.max_test)
        
        if not failed_urls:
            logger.warning("⚠️ 未找到失败的产品URL")
            return
        
        # 如果指定了特定代码，只测试该代码
        if args.specific_code:
            failed_urls = [url for url in failed_urls if url['leaf_code'] == args.specific_code]
            if not failed_urls:
                logger.error(f"❌ 未找到代码为 {args.specific_code} 的失败记录")
                return
        
        logger.info(f"📋 找到 {len(failed_urls)} 个失败的URL待测试")
        
        # 初始化爬虫
        crawler = UltimateProductLinksCrawlerV2(
            log_level=logging.DEBUG if args.debug else logging.INFO,
            headless=args.headless,
            debug_mode=args.debug
        )
        
        test_results = []
        
        with crawler:
            for i, url_info in enumerate(failed_urls, 1):
                logger.info(f"\n🔄 进度: {i}/{len(failed_urls)}")
                
                result = test_single_url(crawler, url_info, logger)
                test_results.append(result)
                
                # 休息一下，避免过于频繁的请求
                if i < len(failed_urls):
                    logger.info(f"😴 休息 3 秒...")
                    time.sleep(3)
        
        # 汇总结果
        logger.info(f"\n{'='*80}")
        logger.info("📊 测试结果汇总")
        logger.info(f"{'='*80}")
        
        success_count = len([r for r in test_results if r['test_result'] == 'success'])
        no_products_count = len([r for r in test_results if r['test_result'] == 'no_products'])
        error_count = len([r for r in test_results if r['test_result'] == 'error'])
        
        logger.info(f"✅ 成功: {success_count} 个")
        logger.info(f"⚠️ 无产品: {no_products_count} 个")
        logger.info(f"❌ 错误: {error_count} 个")
        
        # 详细结果
        for result in test_results:
            status_emoji = {'success': '✅', 'no_products': '⚠️', 'error': '❌'}[result['test_result']]
            logger.info(f"{status_emoji} {result['leaf_code']}: {result['product_count']} 产品 (耗时: {result['test_duration']}s)")
            
            if result['test_result'] == 'success':
                logger.info(f"   目标: {result['target_count']}, 完成度: {result['progress_percentage']:.1f}%")
            elif result['test_result'] == 'error':
                logger.info(f"   错误: {result['error_message']}")
        
        # 保存详细结果
        results_file = BASE_DIR / "results" / f"test_failed_products_results_{int(time.time())}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_tested': len(test_results),
                    'success_count': success_count,
                    'no_products_count': no_products_count,
                    'error_count': error_count,
                    'test_timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                },
                'details': test_results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n💾 详细结果已保存到: {results_file}")
        
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 