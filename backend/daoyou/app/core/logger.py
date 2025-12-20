
import logging
from logging.config import dictConfig
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

class LogConfig(BaseSettings):
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(message)s"
    LOG_DIR: str = "logs"
    APP_LOG_FILE: str = "app.log"
    ERROR_LOG_FILE: str = "error.log"

    class Config:
        case_sensitive = True

def setup_logging():
    """设置日志配置"""
    config = LogConfig()
    
    # 创建日志目录
    Path(config.LOG_DIR).mkdir(exist_ok=True)
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": config.LOG_FORMAT,
                "use_colors": None,
            },
        },
        "handlers": {
            "console": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "formatter": "default",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": f"{config.LOG_DIR}/{config.APP_LOG_FILE}",
                "maxBytes": 1024 * 1024 * 5,  # 5MB
                "backupCount": 5,
                "encoding": "utf8",
            },
            "error_file": {
                "formatter": "default",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": f"{config.LOG_DIR}/{config.ERROR_LOG_FILE}",
                "maxBytes": 1024 * 1024 * 5,
                "backupCount": 5,
                "level": "ERROR",
                "encoding": "utf8",
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file", "error_file"],
                "level": config.LOG_LEVEL,
            },
        },
    }

    dictConfig(logging_config)
