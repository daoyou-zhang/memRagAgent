from __future__ import annotations

import logging
import uuid
from datetime import datetime

from ..models.test_plan import ApiTestExecutionResult
from ..models.test_record import TestRecord, TestStatus, TestType
from ..repositories.memory_repository import test_repository
from .executor_api import execute_api_test_plan
from .planner_service import plan_api_tests_with_llm

logger = logging.getLogger(__name__)


class TestService:
    async def run_api_test(
        self,
        *,
        target: str,
        requirements: str,
        base_url: str | None = None,
    ) -> TestRecord:
        """高层封装：规划 + 执行一次 API 测试，并保存记录。"""

        test_id = str(uuid.uuid4())
        record = TestRecord(
            id=test_id,
            target=target,
            test_type=TestType.API,
            requirements=requirements,
            status=TestStatus.PENDING,
        )
        test_repository.save(record)

        try:
            record.status = TestStatus.RUNNING
            test_repository.save(record)

            # 1) 规划测试计划
            plan = await plan_api_tests_with_llm(
                target=target,
                requirements=requirements,
                base_url=base_url,
            )

            # 2) 执行计划
            api_result: ApiTestExecutionResult = await execute_api_test_plan(plan)

            record.api_result = api_result
            record.success_rate = api_result.success_rate
            record.total_checks = api_result.total_cases
            record.passed_checks = api_result.passed_cases

            record.status = (
                TestStatus.SUCCESS if api_result.success_rate >= 80.0 else TestStatus.FAILED
            )

        except Exception as e:  # noqa: BLE001
            logger.exception("API 测试执行异常: %s", e)
            record.status = TestStatus.FAILED
            record.errors = [str(e)]
        finally:
            record.end_time = datetime.utcnow()
            record.duration = (record.end_time - record.start_time).total_seconds()
            test_repository.save(record)

        return record

    def get_test_record(self, test_id: str) -> TestRecord | None:
        return test_repository.get(test_id)

    def list_test_records(self, limit: int = 50, offset: int = 0):
        # offset 目前简单丢弃使用，仅保留 limit
        return test_repository.list(limit=limit)


test_service = TestService()
