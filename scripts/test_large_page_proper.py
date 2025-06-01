#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大页面性能测试（正确版本）
========================
测试算法在大页面上的表现
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.products import ProductLinksCrawler
from src.utils.browser_manager import create_browser_manager


def test_large_page_proper():
    """测试大页面性能（正确版本）"""
    # 5099产品的大页面
    test_url = "https://www.traceparts.cn/en/search/traceparts-classification-electrical-electrical-protection-devices-circuit-breakers-molded-case-circuit-breakers-mccb?CatalogPath=TRACEPARTS%3ATP09004001008"
    
    print("🎯 大页面性能测试")
    print("=" * 60)
    print(f"测试URL: {test_url}")
    print("说明: 将加载产品直到达到500个或没有更多产品")
    print("模式: 无头模式（生产环境）\n")
    
    # 创建爬取器
    browser_manager = create_browser_manager(pool_size=1)
    crawler = ProductLinksCrawler(browser_manager)
    
    # 保存原始方法
    original_load_all = crawler._load_all_results
    
    # 创建一个限制版本
    def limited_load_all_results(driver):
        """修改版：加载产品直到500个"""
        # 初始滚动
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)
        
        # 记录产品数变化
        last_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
        no_change_count = 0
        click_count = 0
        
        while True:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "a[href*='&Product=']"))
            print(f"  当前产品数: {current_count}")
            
            # 达到500个就停止
            if current_count >= 500:
                print(f"  ✓ 达到500个产品，停止加载")
                crawler.logger.info(f"加载完成，最终产品数: {current_count}")
                break
            
            # 检查是否有变化
            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= 5:
                    print(f"  ✓ 产品数不再变化，停止加载")
                    crawler.logger.info(f"加载完成，最终产品数: {current_count}")
                    break
            else:
                no_change_count = 0
                last_count = current_count
                
            # 智能等待并点击按钮（复制自优化后的代码）
            button_clicked = False
            
            # 首先快速检查按钮是否已存在
            try:
                button = driver.find_element(By.CSS_SELECTOR, "button.more-results")
                if button.is_displayed() and button.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", button)
                    click_count += 1
                    print(f"  ✓ 第 {click_count} 次点击 Show More")
                    button_clicked = True
                    time.sleep(1.5)
                    continue
            except:
                pass
                
            # 如果没找到，等待按钮出现
            if not button_clicked:
                try:
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    
                    button = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "button.more-results"))
                    )
                    if button.is_displayed() and button.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].click();", button)
                        click_count += 1
                        print(f"  ✓ 第 {click_count} 次点击 Show More（等待后）")
                        button_clicked = True
                        time.sleep(1.5)
                except:
                    pass
                    
            # 如果还是没找到按钮，滚动
            if not button_clicked:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                
            # 避免无限循环
            if click_count > 50:  # 500/40 ≈ 13，给充足余量
                print(f"  ⚠️ 已点击 {click_count} 次，停止加载")
                break
    
    # 替换方法
    crawler._load_all_results = limited_load_all_results
    
    try:
        print("⏳ 开始爬取...")
        start_time = time.time()
        
        # 导入必要的模块
        from selenium.webdriver.common.by import By
        
        products = crawler.extract_product_links(test_url)
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"✅ 完成!")
        print(f"  获取产品数: {len(products)}")
        print(f"  用时: {elapsed:.1f} 秒")
        print(f"  速度: {len(products)/elapsed:.1f} 个/秒")
        
        # 评估
        if len(products) >= 500:
            print(f"\n🎉 成功获取500+个产品！")
        elif len(products) >= 400:
            print(f"\n✅ 性能良好！")
        else:
            print(f"\n⚠️  获取产品数较少")
            
        # 预估全部5099个产品的时间
        if len(products) > 0:
            # 更准确的估算：考虑到后面可能会变慢
            avg_speed = len(products) / elapsed
            # 假设速度会逐渐降低
            estimated_time = 5099 / avg_speed * 1.2  # 增加20%的缓冲
            print(f"\n💡 预估获取全部5099个产品需要: {estimated_time:.1f} 秒 ({estimated_time/60:.1f} 分钟)")
            
            # 与test_5099_improved.py对比
            print(f"\n📊 参考: test_5099_improved.py 获取5000个产品用时243.8秒")
            
    finally:
        # 恢复原始方法
        crawler._load_all_results = original_load_all
        browser_manager.shutdown()
        print("\n✅ 测试完成")


if __name__ == '__main__':
    test_large_page_proper() 