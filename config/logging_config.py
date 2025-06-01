#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块
===========
统一管理项目的日志配置
"""

import logging
import logging.handlers
from pathlib import Path
from config.settings import Settings

def setup_logging(name: str = None, level: str = None) -> logging.Logger:
    """
    设置日志配置
    
    Args:
        name: 日志器名称，默认为根日志器
        level: 日志级别，默认从配置读取
        
    Returns:
        配置好的日志器实例
    """
    # 确保日志目录存在
    log_file = Path(Settings.LOGGING['file'])
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 获取或创建日志器
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = level or Settings.LOGGING['level']
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 创建格式化器
    formatter = logging.Formatter(Settings.LOGGING['format'])
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（带日志轮转）
    file_handler = logging.handlers.RotatingFileHandler(
        Settings.LOGGING['file'],
        maxBytes=Settings.LOGGING['max_bytes'],
        backupCount=Settings.LOGGING['backup_count'],
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 阻止日志向上传播
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        日志器实例
    """
    return setup_logging(name)


class LoggerMixin:
    """日志器混入类，为其他类提供日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取类专属的日志器"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__module__ + '.' + self.__class__.__name__)
        return self._logger 