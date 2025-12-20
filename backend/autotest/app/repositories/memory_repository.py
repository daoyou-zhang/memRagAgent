"""一个简单的内存仓库实现，方便在早期阶段不用直接接 Postgres。

后续如果需要，可以很容易地替换为 SQLite 或 Postgres 实现，保持 TestRepository 接口不变。
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..models.test_record import TestRecord, TestStatus, TestType, TestSummary


class InMemoryTestRepository:
    def __init__(self) -> None:
        self._records: Dict[str, TestRecord] = {}

    def save(self, record: TestRecord) -> None:
        self._records[record.id] = record

    def get(self, test_id: str) -> Optional[TestRecord]:
        return self._records.get(test_id)

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: Optional[TestStatus] = None,
        test_type: Optional[TestType] = None,
    ) -> List[TestRecord]:
        items = list(self._records.values())
        if status:
            items = [r for r in items if r.status == status]
        if test_type:
            items = [r for r in items if r.test_type == test_type]
        items.sort(key=lambda r: r.start_time, reverse=True)
        return items[offset : offset + limit]

    def summary(self) -> TestSummary:
        items = list(self._records.values())
        total = len(items)
        successful = len([r for r in items if r.status == TestStatus.SUCCESS])
        failed = len([r for r in items if r.status == TestStatus.FAILED])
        avg_success = (
            sum((r.success_rate or 0) for r in items) / total if total > 0 else 0.0
        )
        avg_duration = (
            sum((r.duration or 0) for r in items) / total if total > 0 else 0.0
        )
        return TestSummary(
            total_tests=total,
            successful_tests=successful,
            failed_tests=failed,
            avg_success_rate=avg_success,
            avg_duration=avg_duration,
        )


test_repository = InMemoryTestRepository()
