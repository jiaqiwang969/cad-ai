#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络守护模块
===========
监控网络异常，自动暂停和恢复
"""

import time
import collections
import threading
from typing import Optional, Callable
from config.settings import Settings
from config.logging_config import LoggerMixin


class NetworkGuard(LoggerMixin):
    """网络异常监控与自动暂停"""
    
    def __init__(self, 
                 fail_window_sec: int = None,
                 fail_threshold: int = None,
                 pause_seconds: int = None,
                 on_pause_callback: Optional[Callable] = None):
        """
        初始化网络守护
        
        Args:
            fail_window_sec: 统计窗口时长（秒）
            fail_threshold: 失败阈值
            pause_seconds: 暂停时长（秒）
            on_pause_callback: 暂停时的回调函数
        """
        self.fail_window_sec = fail_window_sec or Settings.NETWORK['fail_window_sec']
        self.fail_threshold = fail_threshold or Settings.NETWORK['fail_threshold']
        self.pause_seconds = pause_seconds or Settings.NETWORK['pause_seconds']
        self.cooldown_factor = Settings.NETWORK['cooldown_factor']
        
        self._failure_times = collections.deque(maxlen=1000)
        self._lock = threading.Lock()
        self._last_pause_time = 0.0
        self._on_pause_callback = on_pause_callback
        
        # 统计信息
        self._total_failures = 0
        self._total_successes = 0
        self._total_pauses = 0
    
    def _trim(self, now: float):
        """移除窗口之外的时间戳"""
        while self._failure_times and now - self._failure_times[0] > self.fail_window_sec:
            self._failure_times.popleft()
    
    def register_fail(self, error_type: str = 'network'):
        """
        记录一次失败，必要时暂停
        
        Args:
            error_type: 错误类型，用于日志记录
        """
        now = time.time()
        with self._lock:
            self._trim(now)
            self._failure_times.append(now)
            self._total_failures += 1
            
            # 冷却期检查
            cooldown_time = self.pause_seconds * self.cooldown_factor
            if now - self._last_pause_time < cooldown_time:
                self.logger.debug(f"在冷却期内，跳过暂停检查 (剩余 {cooldown_time - (now - self._last_pause_time):.1f}s)")
                return
            
            # 检查是否需要暂停
            if len(self._failure_times) >= self.fail_threshold:
                self._total_pauses += 1
                self.logger.warning(
                    f"🌐 网络异常触发暂停: {len(self._failure_times)} 次失败 "
                    f"(窗口 {self.fail_window_sec}s), 暂停 {self.pause_seconds}s ... "
                    f"[类型: {error_type}]"
                )
                self._last_pause_time = now
                
                # 执行暂停回调
                if self._on_pause_callback:
                    try:
                        self._on_pause_callback()
                    except Exception as e:
                        self.logger.error(f"暂停回调执行失败: {e}")
        
        # 在锁外执行暂停
        if now == self._last_pause_time:
            time.sleep(self.pause_seconds)
    
    def register_success(self):
        """成功访问后修剪旧记录"""
        now = time.time()
        with self._lock:
            self._trim(now)
            self._total_successes += 1
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            current_failures = len(self._failure_times)
            success_rate = self._total_successes / (self._total_successes + self._total_failures) \
                if (self._total_successes + self._total_failures) > 0 else 0
        
        return {
            'total_failures': self._total_failures,
            'total_successes': self._total_successes,
            'total_pauses': self._total_pauses,
            'current_failures_in_window': current_failures,
            'success_rate': success_rate,
            'last_pause_time': self._last_pause_time,
        }
    
    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self._total_failures = 0
            self._total_successes = 0
            self._total_pauses = 0
            self._failure_times.clear()
    
    def is_healthy(self) -> bool:
        """检查网络是否健康"""
        with self._lock:
            self._trim(time.time())
            return len(self._failure_times) < self.fail_threshold


# 全局实例
_global_guard = NetworkGuard()

# 便捷函数
def register_fail(error_type: str = 'network'):
    """记录失败"""
    _global_guard.register_fail(error_type)

def register_success():
    """记录成功"""
    _global_guard.register_success()

def get_network_stats() -> dict:
    """获取网络统计"""
    return _global_guard.get_stats()

def is_network_healthy() -> bool:
    """检查网络健康状态"""
    return _global_guard.is_healthy() 