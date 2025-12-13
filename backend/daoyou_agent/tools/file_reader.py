"""文件读取工具 - 支持读取指定路径的代码文件

安全限制：
- 只允许读取文本类文件
- 文件大小限制（默认 1MB）
- 可配置允许的目录白名单
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

# 允许读取的文件扩展名
ALLOWED_EXTENSIONS = {
    # 代码文件
    '.py', '.js', '.ts', '.jsx', '.tsx', '.vue', '.java', '.c', '.cpp', '.h',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.cs',
    # 配置文件
    '.json', '.yaml', '.yml', '.toml', '.ini', '.env', '.xml',
    # 文档文件
    '.md', '.txt', '.rst', '.csv',
    # Web 文件
    '.html', '.css', '.scss', '.less',
    # Shell 脚本
    '.sh', '.bash', '.zsh', '.bat', '.ps1',
    # SQL
    '.sql',
}

# 最大文件大小（字节）
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB

# 目录白名单（可选，为空表示不限制）
ALLOWED_DIRECTORIES: List[str] = []


def read_file(
    file_path: str,
    encoding: str = "utf-8",
    max_lines: Optional[int] = None,
    start_line: int = 1,
) -> Dict[str, Any]:
    """读取指定路径的文件内容
    
    Args:
        file_path: 文件绝对路径或相对路径
        encoding: 文件编码（默认 utf-8）
        max_lines: 最大读取行数（可选）
        start_line: 起始行号（1-indexed，默认 1）
    
    Returns:
        {
            "success": bool,
            "content": str,         # 文件内容
            "file_path": str,       # 规范化后的路径
            "file_name": str,       # 文件名
            "extension": str,       # 扩展名
            "total_lines": int,     # 总行数
            "read_lines": int,      # 实际读取行数
            "file_size": int,       # 文件大小（字节）
            "error": str,           # 错误信息（如果有）
        }
    """
    result = {
        "success": False,
        "content": "",
        "file_path": "",
        "file_name": "",
        "extension": "",
        "total_lines": 0,
        "read_lines": 0,
        "file_size": 0,
        "error": "",
    }
    
    try:
        # 规范化路径
        path = Path(file_path).resolve()
        result["file_path"] = str(path)
        result["file_name"] = path.name
        result["extension"] = path.suffix.lower()
        
        # 检查文件是否存在
        if not path.exists():
            result["error"] = f"文件不存在: {path}"
            return result
        
        if not path.is_file():
            result["error"] = f"不是有效文件: {path}"
            return result
        
        # 检查扩展名
        if result["extension"] not in ALLOWED_EXTENSIONS:
            result["error"] = f"不支持的文件类型: {result['extension']}，允许: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            return result
        
        # 检查文件大小
        file_size = path.stat().st_size
        result["file_size"] = file_size
        if file_size > MAX_FILE_SIZE:
            result["error"] = f"文件过大: {file_size / 1024 / 1024:.2f}MB，最大允许: {MAX_FILE_SIZE / 1024 / 1024:.2f}MB"
            return result
        
        # 检查目录白名单
        if ALLOWED_DIRECTORIES:
            allowed = False
            for allowed_dir in ALLOWED_DIRECTORIES:
                if str(path).startswith(allowed_dir):
                    allowed = True
                    break
            if not allowed:
                result["error"] = f"目录不在白名单中: {path.parent}"
                return result
        
        # 读取文件
        with open(path, "r", encoding=encoding, errors="replace") as f:
            all_lines = f.readlines()
        
        result["total_lines"] = len(all_lines)
        
        # 处理行范围
        start_idx = max(0, start_line - 1)
        if max_lines:
            end_idx = min(start_idx + max_lines, len(all_lines))
        else:
            end_idx = len(all_lines)
        
        selected_lines = all_lines[start_idx:end_idx]
        result["read_lines"] = len(selected_lines)
        
        # 添加行号
        numbered_lines = []
        for i, line in enumerate(selected_lines, start=start_idx + 1):
            numbered_lines.append(f"{i:4d} | {line.rstrip()}")
        
        result["content"] = "\n".join(numbered_lines)
        result["success"] = True
        
        logger.info(f"[FileReader] 读取文件: {path.name}, {result['read_lines']}/{result['total_lines']} 行")
        
    except UnicodeDecodeError as e:
        result["error"] = f"编码错误: {e}，尝试使用其他 encoding 参数"
    except PermissionError:
        result["error"] = f"权限不足，无法读取文件"
    except Exception as e:
        result["error"] = f"读取失败: {str(e)}"
        logger.error(f"[FileReader] 读取文件失败: {e}")
    
    return result


def list_directory(
    dir_path: str,
    pattern: str = "*",
    recursive: bool = False,
    max_items: int = 100,
) -> Dict[str, Any]:
    """列出目录内容
    
    Args:
        dir_path: 目录路径
        pattern: 匹配模式（如 *.py）
        recursive: 是否递归子目录
        max_items: 最大返回数量
    
    Returns:
        {
            "success": bool,
            "items": List[Dict],    # 文件/目录列表
            "total_count": int,
            "error": str,
        }
    """
    result = {
        "success": False,
        "items": [],
        "total_count": 0,
        "error": "",
    }
    
    try:
        path = Path(dir_path).resolve()
        
        if not path.exists():
            result["error"] = f"目录不存在: {path}"
            return result
        
        if not path.is_dir():
            result["error"] = f"不是有效目录: {path}"
            return result
        
        # 获取文件列表
        if recursive:
            items = list(path.rglob(pattern))
        else:
            items = list(path.glob(pattern))
        
        result["total_count"] = len(items)
        
        # 限制数量并格式化
        for item in items[:max_items]:
            item_info = {
                "name": item.name,
                "path": str(item),
                "is_file": item.is_file(),
                "is_dir": item.is_dir(),
                "extension": item.suffix.lower() if item.is_file() else "",
                "size": item.stat().st_size if item.is_file() else 0,
            }
            result["items"].append(item_info)
        
        result["success"] = True
        logger.info(f"[FileReader] 列出目录: {path}, {len(result['items'])}/{result['total_count']} 项")
        
    except Exception as e:
        result["error"] = f"列目录失败: {str(e)}"
        logger.error(f"[FileReader] 列目录失败: {e}")
    
    return result


# 工具元数据（供 MCP 注册使用）
TOOL_METADATA = {
    "read_file": {
        "name": "read_file",
        "description": "读取指定路径的代码/文本文件内容",
        "category": "file",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件路径"},
                "encoding": {"type": "string", "default": "utf-8"},
                "max_lines": {"type": "integer", "description": "最大读取行数"},
                "start_line": {"type": "integer", "default": 1, "description": "起始行号"},
            },
            "required": ["file_path"],
        },
    },
    "list_directory": {
        "name": "list_directory",
        "description": "列出目录中的文件和子目录",
        "category": "file",
        "input_schema": {
            "type": "object",
            "properties": {
                "dir_path": {"type": "string", "description": "目录路径"},
                "pattern": {"type": "string", "default": "*", "description": "匹配模式"},
                "recursive": {"type": "boolean", "default": False},
                "max_items": {"type": "integer", "default": 100},
            },
            "required": ["dir_path"],
        },
    },
}
