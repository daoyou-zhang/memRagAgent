from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


class ValidationRule(BaseModel):
    """单条断言规则。

    - type: 断言类型，如 status_code/json_field/contains/header
    - path: 针对 JSON 时的字段路径（支持点号或 JSONPath 子集），非 JSON 时可为空
    - expected: 期望值
    - op: 比较操作符，如 eq, ne, gt, lt, contains, not_contains, in, not_in
    """

    type: Literal["status_code", "json_field", "contains", "header"] = "json_field"
    path: Optional[str] = None
    expected: Any = None
    op: str = Field(default="eq", description="比较操作符，例如 eq/contains/in 等")


class ApiTestCase(BaseModel):
    """单条 API 测试用例。"""

    name: str
    description: Optional[str] = None

    method: HttpMethod = "GET"
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    query: Dict[str, Any] = Field(default_factory=dict)
    body: Optional[Any] = None

    # 断言规则集合
    validations: List[ValidationRule] = Field(default_factory=list)


class ApiTestPlan(BaseModel):
    """API 测试计划，由 LLM 规划或人工编写。"""

    target: str = Field(..., description="被测服务或 API 的标识")
    requirements: str = Field(..., description="自然语言测试需求描述")

    base_url: Optional[str] = Field(
        default=None,
        description="可选：统一的基础 URL，若为 None 则用 case.url 作为完整地址",
    )

    cases: List[ApiTestCase] = Field(default_factory=list)


class ApiTestCaseResult(BaseModel):
    """单条用例的执行结果。"""

    case_name: str
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    failed_validations: List[str] = Field(default_factory=list)
    raw_response: Optional[Any] = None


class ApiTestExecutionResult(BaseModel):
    """一次 API 测试计划执行的汇总结果。"""

    success_rate: float
    total_cases: int
    passed_cases: int
    failed_cases: int
    case_results: List[ApiTestCaseResult] = Field(default_factory=list)
