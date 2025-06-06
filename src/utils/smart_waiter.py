#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能等待策略
==========
根据页面类型和加载状态动态调整等待时间
"""

import time
import logging
from typing import Callable, Any, Optional
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException


class SmartWaiter:
    """智能等待器"""
    
    def __init__(self, driver, logger=None):
        self.driver = driver
        self.logger = logger or logging.getLogger(__name__)
        
        # 不同页面类型的等待配置
        self.wait_configs = {
            'industrietechnik': {
                'base_wait': 5,
                'content_wait': 10,
                'ajax_wait': 15,
                'retry_interval': 2
            },
            'apostoli': {
                'base_wait': 2,
                'content_wait': 5,
                'ajax_wait': 8,
                'retry_interval': 1
            },
            'default': {
                'base_wait': 3,
                'content_wait': 8,
                'ajax_wait': 12,
                'retry_interval': 1.5
            }
        }
    
    def wait_for_page_ready(self, page_type: str = 'default') -> bool:
        """等待页面就绪"""
        config = self.wait_configs.get(page_type, self.wait_configs['default'])
        
        try:
            # 1. 基础DOM就绪
            self.logger.debug(f"⏳ 等待基础DOM就绪...")
            WebDriverWait(self.driver, config['base_wait']).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 2. 等待主要内容加载
            self.logger.debug(f"⏳ 等待主要内容加载...")
            self._wait_for_content_loaded(config['content_wait'])
            
            # 3. 等待AJAX完成
            self.logger.debug(f"⏳ 等待AJAX完成...")
            self._wait_for_ajax_complete(config['ajax_wait'])
            
            # 4. 额外缓冲时间
            time.sleep(config['retry_interval'])
            
            self.logger.debug(f"✅ 页面就绪完成 ({page_type})")
            return True
            
        except TimeoutException as e:
            self.logger.warning(f"⚠️ 页面等待超时 ({page_type}): {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ 页面等待失败 ({page_type}): {e}")
            return False
    
    def _wait_for_content_loaded(self, timeout: int) -> bool:
        """等待主要内容加载"""
        try:
            # 等待表格或规格容器出现
            WebDriverWait(self.driver, timeout).until(
                lambda d: (
                    len(d.find_elements(By.TAG_NAME, 'table')) > 0 or
                    len(d.find_elements(By.XPATH, "//div[contains(@class, 'spec')]")) > 0 or
                    len(d.find_elements(By.XPATH, "//div[contains(@class, 'product')]")) > 0 or
                    len(d.find_elements(By.XPATH, "//div[contains(@class, 'technical')]")) > 0
                )
            )
            return True
        except TimeoutException:
            self.logger.debug("主要内容等待超时")
            return False
    
    def _wait_for_ajax_complete(self, timeout: int) -> bool:
        """等待AJAX请求完成"""
        try:
            # 检查jQuery活动请求
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return jQuery.active == 0") if self._has_jquery() else True
            )
            
            # 检查Angular请求
            if self._has_angular():
                WebDriverWait(self.driver, timeout).until(
                    lambda d: d.execute_script("return window.getAllAngularTestabilities().findIndex(x=>!x.isStable()) === -1")
                )
            
            # 检查Fetch/XHR请求（通用方法）
            self._wait_for_network_idle(min(timeout, 5))
            
            return True
        except TimeoutException:
            self.logger.debug("AJAX等待超时")
            return False
        except Exception as e:
            self.logger.debug(f"AJAX检查失败: {e}")
            return False
    
    def _has_jquery(self) -> bool:
        """检查页面是否有jQuery"""
        try:
            return self.driver.execute_script("return typeof jQuery !== 'undefined'")
        except:
            return False
    
    def _has_angular(self) -> bool:
        """检查页面是否有Angular"""
        try:
            return self.driver.execute_script("return typeof window.getAllAngularTestabilities === 'function'")
        except:
            return False
    
    def _wait_for_network_idle(self, timeout: int) -> bool:
        """等待网络空闲"""
        try:
            start_time = time.time()
            stable_count = 0
            required_stable_count = 3  # 需要连续3次检查都稳定
            
            while time.time() - start_time < timeout:
                # 检查页面是否还在加载
                ready_state = self.driver.execute_script("return document.readyState")
                if ready_state == 'complete':
                    stable_count += 1
                else:
                    stable_count = 0
                
                if stable_count >= required_stable_count:
                    return True
                
                time.sleep(0.5)
            
            return False
        except Exception:
            return False
    
    def wait_for_element_visible(self, locator: tuple, timeout: int = 10) -> bool:
        """等待元素可见"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return True
        except TimeoutException:
            return False
    
    def wait_for_elements_present(self, locator: tuple, min_count: int = 1, timeout: int = 10) -> bool:
        """等待指定数量的元素出现"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: len(d.find_elements(*locator)) >= min_count
            )
            return True
        except TimeoutException:
            return False
    
    def wait_with_retry(self, condition: Callable, max_retries: int = 3, retry_interval: float = 2) -> Any:
        """带重试的等待"""
        for attempt in range(max_retries):
            try:
                result = condition()
                if result:
                    return result
            except Exception as e:
                self.logger.debug(f"等待条件失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
        
        return None
    
    def adaptive_wait_for_specs(self, page_type: str = 'default') -> bool:
        """自适应等待规格数据"""
        config = self.wait_configs.get(page_type, self.wait_configs['default'])
        
        def check_specs_ready():
            """检查规格数据是否就绪"""
            try:
                # 检查表格
                tables = self.driver.find_elements(By.TAG_NAME, 'table')
                if tables:
                    for table in tables:
                        if table.is_displayed():
                            rows = table.find_elements(By.TAG_NAME, 'tr')
                            if len(rows) >= 2:  # 至少有标题行和数据行
                                return True
                
                # 检查规格容器
                spec_containers = self.driver.find_elements(By.XPATH, 
                    "//div[contains(@class, 'spec') or contains(@class, 'technical') or contains(@class, 'detail')]")
                
                for container in spec_containers:
                    if container.is_displayed() and container.text.strip():
                        return True
                
                return False
            except Exception:
                return False
        
        # 使用重试机制等待规格数据
        result = self.wait_with_retry(
            check_specs_ready,
            max_retries=3,
            retry_interval=config['retry_interval']
        )
        
        if result:
            self.logger.debug(f"✅ 规格数据就绪 ({page_type})")
        else:
            self.logger.warning(f"⚠️ 规格数据未就绪 ({page_type})")
        
        return bool(result)