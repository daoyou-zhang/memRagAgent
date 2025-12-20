from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .test_plan import ApiTestExecutionResult


class TestType(str, Enum):
    """测试类型。"""

    API = "api"
    UI = "ui"
    LINK = "link"


class TestStatus(str, Enum):
    """测试状态。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class TestRecord(BaseModel):
    """一次测试执行的记录（简化版本，先存到 SQLite 或内存）。"""

    id: str
    target: str
    test_type: TestType = TestType.API
    requirements: str

    status: TestStatus = TestStatus.PENDING

    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None

    # 结果概要
    success_rate: Optional[float] = None
    total_checks: Optional[int] = None
    passed_checks: Optional[int] = None

    # 详细结果（目前主要放 API 执行结果）
    api_result: Optional[ApiTestExecutionResult] = None

    # AI 分析与建议
    ai_analysis: Optional[str] = None
    recommendations: Optional[List[str]] = None

    errors: Optional[List[str]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class TestSummary(BaseModel):
    total_tests: int = 0
    successful_tests: int = 0
    failed_tests: int = 0
    avg_success_rate: float = 0.0
    avg_duration: float = 0.0
