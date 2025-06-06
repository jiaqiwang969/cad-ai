#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能线程池管理器
==============
解决并发冲突和资源竞争问题
"""

import time
import logging
import threading
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from queue import Queue, Empty
from dataclasses import dataclass
from enum import Enum


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    """任务对象"""
    id: str
    url: str
    vendor: str
    priority: TaskPriority
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class SmartThreadPool:
    """智能线程池管理器"""
    
    def __init__(self, max_workers: int = 12, logger=None):
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 任务队列 - 按优先级分组
        self.task_queues = {
            TaskPriority.URGENT: Queue(),
            TaskPriority.HIGH: Queue(),
            TaskPriority.NORMAL: Queue(),
            TaskPriority.LOW: Queue()
        }
        
        # 线程本地存储 - 每个线程独立的资源
        self.thread_local = threading.local()
        
        # 并发控制
        self.active_tasks = {}  # 正在执行的任务
        self.completed_tasks = {}  # 已完成的任务
        self.failed_tasks = {}  # 失败的任务
        
        # 性能监控
        self.stats = {
            'total_submitted': 0,
            'total_completed': 0,
            'total_failed': 0,
            'avg_processing_time': 0,
            'vendor_stats': {}
        }
        
        # 供应商特定的并发限制
        self.vendor_limits = {
            'industrietechnik': 3,     # industrietechnik限制较严格
            'apostoli': 6,             # apostoli可以更高并发
            'skf': 8,                  # SKF是大供应商，可以较高并发
            'timken': 6,               # Timken中等并发
            'ntn': 6,                  # NTN中等并发
            'winco': 4,                # Winco较小并发
            'smc': 8,                  # SMC较高并发
            'essentra': 4,             # Essentra较小并发
            'traceparts': 2,           # TraceParts自有产品，可能有特殊限制
            'record': 4,               # Record中等并发
            'generic': max_workers     # generic使用全部并发
        }
        
        # 当前每个供应商的活跃任务数
        self.vendor_active_count = {}
        self.vendor_lock = threading.Lock()
        
        # 错误率监控
        self.error_windows = {}  # 滑动窗口错误率
        self.error_threshold = 0.3  # 30%错误率阈值
        self.cooldown_vendors = set()  # 正在冷却的供应商
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_performance, daemon=True)
        self.monitor_thread.start()
    
    def submit_task(self, task: Task, processor: Callable) -> Future:
        """提交任务"""
        self.stats['total_submitted'] += 1
        
        # 检查供应商是否在冷却期
        if task.vendor in self.cooldown_vendors:
            self.logger.warning(f"🧊 供应商 {task.vendor} 正在冷却期，延迟处理")
            time.sleep(2)
        
        # 包装处理函数
        def wrapped_processor():
            return self._execute_task_with_monitoring(task, processor)
        
        # 提交到线程池
        future = self.executor.submit(wrapped_processor)
        
        # 记录活跃任务
        self.active_tasks[task.id] = {
            'task': task,
            'future': future,
            'start_time': time.time()
        }
        
        return future
    
    def _execute_task_with_monitoring(self, task: Task, processor: Callable) -> Dict[str, Any]:
        """执行任务并监控性能"""
        start_time = time.time()
        
        # 检查供应商并发限制 - 使用更智能的等待策略
        max_wait_attempts = 10
        wait_time = 0.1
        
        for attempt in range(max_wait_attempts):
            if self._acquire_vendor_slot(task.vendor):
                break
            
            if attempt == 0:
                self.logger.warning(f"⚠️ 供应商 {task.vendor} 并发已满，等待...")
            
            time.sleep(wait_time)
            wait_time = min(wait_time * 1.5, 2.0)  # 指数退避，最大2秒
        else:
            # 如果等待超时，仍然尝试处理，但使用降级策略
            self.logger.error(f"❌ 供应商 {task.vendor} 等待超时，跳过任务")
            return {
                'success': False,
                'error': f'Vendor {task.vendor} concurrency wait timeout',
                'task_id': task.id
            }
        
        try:
            # 获取线程专用资源
            thread_resources = self._get_thread_resources(task.vendor)
            
            # 执行任务
            result = processor(task, thread_resources)
            
            # 记录成功
            processing_time = time.time() - start_time
            self._record_success(task, processing_time)
            
            self.logger.debug(f"✅ 任务完成: {task.id} ({processing_time:.2f}s)")
            
            return {
                'success': True,
                'result': result,
                'processing_time': processing_time,
                'task_id': task.id
            }
            
        except Exception as e:
            # 记录失败
            processing_time = time.time() - start_time
            self._record_failure(task, str(e), processing_time)
            
            self.logger.error(f"❌ 任务失败: {task.id} - {e}")
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': processing_time,
                'task_id': task.id
            }
            
        finally:
            # 释放供应商槽位
            self._release_vendor_slot(task.vendor)
            
            # 清理活跃任务记录
            if task.id in self.active_tasks:
                del self.active_tasks[task.id]
    
    def _acquire_vendor_slot(self, vendor: str) -> bool:
        """获取供应商并发槽位"""
        with self.vendor_lock:
            current_count = self.vendor_active_count.get(vendor, 0)
            limit = self.vendor_limits.get(vendor, self.vendor_limits['generic'])
            
            if current_count < limit:
                self.vendor_active_count[vendor] = current_count + 1
                return True
            return False
    
    def _release_vendor_slot(self, vendor: str):
        """释放供应商并发槽位"""
        with self.vendor_lock:
            current_count = self.vendor_active_count.get(vendor, 0)
            if current_count > 0:
                self.vendor_active_count[vendor] = current_count - 1
    
    def _get_thread_resources(self, vendor: str) -> Dict[str, Any]:
        """获取线程专用资源"""
        if not hasattr(self.thread_local, 'resources'):
            from src.utils.anti_detection import AntiDetectionManager
            from src.utils.smart_waiter import SmartWaiter
            
            # 为每个线程创建独立的资源
            anti_detection = AntiDetectionManager(self.logger)
            chrome_options = anti_detection.get_optimized_chrome_options(vendor)
            
            # 创建driver
            from selenium import webdriver
            driver = webdriver.Chrome(options=chrome_options)
            anti_detection.setup_driver_stealth(driver)
            
            # 创建智能等待器
            waiter = SmartWaiter(driver, self.logger)
            
            self.thread_local.resources = {
                'driver': driver,
                'waiter': waiter,
                'anti_detection': anti_detection,
                'vendor': vendor,
                'created_at': time.time()
            }
            
            self.logger.debug(f"🔧 为线程创建资源 (vendor: {vendor})")
        
        return self.thread_local.resources
    
    def _record_success(self, task: Task, processing_time: float):
        """记录成功任务"""
        self.stats['total_completed'] += 1
        self.completed_tasks[task.id] = {
            'task': task,
            'processing_time': processing_time,
            'completed_at': time.time()
        }
        
        # 更新供应商统计
        if task.vendor not in self.stats['vendor_stats']:
            self.stats['vendor_stats'][task.vendor] = {
                'success': 0, 'failed': 0, 'avg_time': 0
            }
        
        vendor_stats = self.stats['vendor_stats'][task.vendor]
        vendor_stats['success'] += 1
        
        # 更新平均时间
        total_success = vendor_stats['success']
        vendor_stats['avg_time'] = (
            (vendor_stats['avg_time'] * (total_success - 1) + processing_time) / total_success
        )
        
        # 更新错误率窗口
        self._update_error_window(task.vendor, success=True)
    
    def _record_failure(self, task: Task, error: str, processing_time: float):
        """记录失败任务"""
        self.stats['total_failed'] += 1
        self.failed_tasks[task.id] = {
            'task': task,
            'error': error,
            'processing_time': processing_time,
            'failed_at': time.time()
        }
        
        # 更新供应商统计
        if task.vendor not in self.stats['vendor_stats']:
            self.stats['vendor_stats'][task.vendor] = {
                'success': 0, 'failed': 0, 'avg_time': 0
            }
        
        self.stats['vendor_stats'][task.vendor]['failed'] += 1
        
        # 更新错误率窗口
        self._update_error_window(task.vendor, success=False)
        
        # 检查是否需要冷却
        self._check_vendor_cooldown(task.vendor)
    
    def _update_error_window(self, vendor: str, success: bool):
        """更新错误率滑动窗口"""
        if vendor not in self.error_windows:
            self.error_windows[vendor] = []
        
        window = self.error_windows[vendor]
        current_time = time.time()
        
        # 添加当前结果
        window.append({
            'timestamp': current_time,
            'success': success
        })
        
        # 清理5分钟前的记录
        window[:] = [r for r in window if current_time - r['timestamp'] < 300]
    
    def _check_vendor_cooldown(self, vendor: str):
        """检查供应商是否需要冷却"""
        if vendor not in self.error_windows:
            return
        
        window = self.error_windows[vendor]
        if len(window) < 10:  # 样本太少，不进行判断
            return
        
        # 计算错误率
        failed_count = sum(1 for r in window if not r['success'])
        error_rate = failed_count / len(window)
        
        if error_rate > self.error_threshold and vendor not in self.cooldown_vendors:
            self.logger.warning(f"🧊 供应商 {vendor} 错误率过高 ({error_rate:.1%})，启动冷却")
            self.cooldown_vendors.add(vendor)
            
            # 10秒后自动解除冷却
            def remove_cooldown():
                time.sleep(10)
                self.cooldown_vendors.discard(vendor)
                self.logger.info(f"🔥 供应商 {vendor} 冷却结束")
            
            threading.Thread(target=remove_cooldown, daemon=True).start()
    
    def _monitor_performance(self):
        """性能监控线程"""
        while True:
            try:
                time.sleep(30)  # 每30秒监控一次
                
                active_count = len(self.active_tasks)
                total_processed = self.stats['total_completed'] + self.stats['total_failed']
                
                if total_processed > 0:
                    success_rate = self.stats['total_completed'] / total_processed
                    self.logger.info(
                        f"📊 线程池状态: 活跃={active_count}, "
                        f"成功率={success_rate:.1%}, "
                        f"已处理={total_processed}"
                    )
                
                # 清理过期资源
                self._cleanup_expired_resources()
                
            except Exception as e:
                self.logger.error(f"性能监控失败: {e}")
    
    def _cleanup_expired_resources(self):
        """清理过期的线程资源"""
        try:
            current_time = time.time()
            
            # 清理超过1小时的线程资源
            for thread_id in list(threading.enumerate()):
                if hasattr(thread_id, 'thread_local'):
                    resources = getattr(thread_id.thread_local, 'resources', None)
                    if resources and current_time - resources['created_at'] > 3600:
                        try:
                            if 'driver' in resources:
                                resources['driver'].quit()
                            delattr(thread_id.thread_local, 'resources')
                            self.logger.debug("🧹 清理过期线程资源")
                        except Exception as e:
                            self.logger.debug(f"资源清理失败: {e}")
                            
        except Exception as e:
            self.logger.debug(f"资源清理过程失败: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        total_processed = self.stats['total_completed'] + self.stats['total_failed']
        success_rate = self.stats['total_completed'] / total_processed if total_processed > 0 else 0
        
        return {
            'total_submitted': self.stats['total_submitted'],
            'total_completed': self.stats['total_completed'],
            'total_failed': self.stats['total_failed'],
            'success_rate': success_rate,
            'active_tasks': len(self.active_tasks),
            'vendor_stats': self.stats['vendor_stats'],
            'cooldown_vendors': list(self.cooldown_vendors)
        }
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """等待所有任务完成"""
        start_time = time.time()
        
        while self.active_tasks:
            if timeout and (time.time() - start_time) > timeout:
                self.logger.warning(f"⏰ 等待超时，仍有 {len(self.active_tasks)} 个任务未完成")
                return False
            
            time.sleep(1)
        
        return True
    
    def shutdown(self, wait: bool = True):
        """关闭线程池"""
        self.logger.info("🛑 关闭线程池...")
        
        # 清理所有线程资源
        for thread_id in threading.enumerate():
            if hasattr(thread_id, 'thread_local'):
                resources = getattr(thread_id.thread_local, 'resources', None)
                if resources and 'driver' in resources:
                    try:
                        resources['driver'].quit()
                    except Exception as e:
                        self.logger.debug(f"Driver关闭失败: {e}")
        
        # 关闭线程池
        self.executor.shutdown(wait=wait)
        
        # 打印最终统计
        stats = self.get_performance_stats()
        self.logger.info(f"📊 最终统计: {stats}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()