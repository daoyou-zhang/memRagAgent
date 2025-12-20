from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models.test_record import TestRecord
from ..services.test_service import test_service

router = APIRouter(prefix="/autotest", tags=["autotest"])


class RunApiTestRequest(BaseModel):
    target: str = Field(..., description="被测 API 完整 URL 或相对路径")
    requirements: str = Field(..., description="自然语言测试需求描述")
    base_url: Optional[str] = Field(
        default=None,
        description="可选基础 URL，若提供则 target 视为相对路径",
    )


class RunApiTestResponse(BaseModel):
    record: TestRecord


@router.post("/run-api-test", response_model=RunApiTestResponse)
async def run_api_test(req: RunApiTestRequest) -> RunApiTestResponse:
    """触发一次 LLM 驱动的 API 测试。

    目前：
    - 由占位 planner 生成一个最简单的用例（检查 200）
    - executor 真实发起 HTTP 请求并做断言
    - 将结果保存在内存仓库中
    """

    try:
        record = await test_service.run_api_test(
            target=req.target,
            requirements=req.requirements,
            base_url=req.base_url,
        )
        return RunApiTestResponse(record=record)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
