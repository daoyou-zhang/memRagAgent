import time
from typing import Any, Dict

import httpx

from ..models.test_plan import (
    ApiTestCase,
    ApiTestExecutionResult,
    ApiTestCaseResult,
    ApiTestPlan,
    ValidationRule,
)


def _check_rule(rule: ValidationRule, *, status_code: int, json_body: Any, text: str, headers: Dict[str, str]) -> (bool, str | None):
    """执行一条校验规则，返回 (是否通过, 失败原因)。"""

    try:
        if rule.type == "status_code":
            expected = int(rule.expected)
            ok = status_code == expected if rule.op == "eq" else status_code != expected
            if not ok:
                return False, f"status_code {status_code} op {rule.op} {expected} 失败"
            return True, None

        if rule.type == "contains":
            s = str(rule.expected)
            if rule.op == "contains":
                ok = s in text
            elif rule.op == "not_contains":
                ok = s not in text
            else:
                return False, f"不支持的 op: {rule.op}"
            if not ok:
                return False, f"响应体不满足 {rule.op} '{s}'"
            return True, None

        if rule.type == "header":
            key = rule.path or ""
            expected = str(rule.expected)
            val = headers.get(key)
            if rule.op == "eq":
                ok = val == expected
            elif rule.op == "contains":
                ok = val is not None and expected in val
            else:
                return False, f"不支持的 header op: {rule.op}"
            if not ok:
                return False, f"header[{key}] 校验失败，实际='{val}' 期望 op={rule.op} '{expected}'"
            return True, None

        if rule.type == "json_field":
            # 简化：仅支持 a.b.c 形式路径
            if json_body is None:
                return False, "响应不是 JSON，无法校验 json_field"
            parts = (rule.path or "").split(".") if rule.path else []
            cur: Any = json_body
            for p in parts:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    return False, f"json_field 路径 '{rule.path}' 不存在"
            val = cur
            exp = rule.expected
            op = rule.op or "eq"
            if op == "eq":
                ok = val == exp
            elif op == "ne":
                ok = val != exp
            elif op == "contains":
                ok = exp in str(val)
            elif op == "not_contains":
                ok = exp not in str(val)
            else:
                return False, f"不支持的 json_field op: {op}"
            if not ok:
                return False, f"json_field '{rule.path}' 校验失败，实际={val!r} op {op} 期望={exp!r}"
            return True, None

        return False, f"未知的规则类型: {rule.type}"
    except Exception as e:
        return False, f"规则执行异常: {e}"


async def execute_api_test_plan(plan: ApiTestPlan) -> ApiTestExecutionResult:
    """执行一份 API 测试计划，返回汇总结果。"""

    results: list[ApiTestCaseResult] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for case in plan.cases:
            url = plan.base_url.rstrip("/") + case.url if plan.base_url else case.url
            t0 = time.perf_counter()
            status_code = None
            text = ""
            json_body: Any = None
            headers: Dict[str, str] = {}
            failed: list[str] = []
            error: str | None = None

            try:
                resp = await client.request(
                    method=case.method,
                    url=url,
                    params=case.query or None,
                    json=case.body,
                    headers=case.headers or None,
                )
                status_code = resp.status_code
                text = resp.text
                headers = dict(resp.headers)
                try:
                    json_body = resp.json()
                except Exception:
                    json_body = None

                for rule in case.validations:
                    ok, reason = _check_rule(
                        rule,
                        status_code=status_code,
                        json_body=json_body,
                        text=text,
                        headers=headers,
                    )
                    if not ok and reason:
                        failed.append(reason)

            except Exception as e:
                error = str(e)

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            success = error is None and not failed

            case_result = ApiTestCaseResult(
                case_name=case.name,
                success=success,
                status_code=status_code,
                response_time_ms=elapsed_ms,
                error=error,
                failed_validations=failed,
                raw_response=json_body if json_body is not None else text,
            )
            results.append(case_result)

    total = len(results)
    passed = len([r for r in results if r.success])
    failed_count = total - passed
    success_rate = (passed / total * 100.0) if total > 0 else 0.0

    return ApiTestExecutionResult(
        success_rate=success_rate,
        total_cases=total,
        passed_cases=passed,
        failed_cases=failed_count,
        case_results=results,
    )
