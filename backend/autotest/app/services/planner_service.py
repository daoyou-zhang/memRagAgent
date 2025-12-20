"""Autotest planner：优先调用本地 daoyou_agent 生成 API 测试计划。

如果本地可用 daoyou_agent 的 CognitiveController，则：
- 构造 CognitiveRequest（agent_id="autotest_planner"），
- 让大模型返回一个描述 ApiTestPlan 的 JSON，
- 解析为 ApiTestPlan/ApiTestCase/ValidationRule。

若导入或调用/解析失败，则退化为基于目标 URL 的简单 200 健康检查计划。
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict

from ..models.test_plan import ApiTestPlan, ApiTestCase, ValidationRule

logger = logging.getLogger(__name__)

try:  # 尝试导入本地 daoyou_agent
    from daoyou_agent.models.cognitive import CognitiveRequest
    from daoyou_agent.services.cognitive_controller import get_cognitive_controller

    _controller = get_cognitive_controller()
except Exception as e:  # noqa: BLE001
    CognitiveRequest = None  # type: ignore[assignment]
    get_cognitive_controller = None  # type: ignore[assignment]
    _controller = None
    logger.warning("daoyou_agent 不可用，Autotest planner 将使用占位计划: %s", e)


def _fallback_plan(target: str, requirements: str, base_url: str | None) -> ApiTestPlan:
    """兜底：构造一份简单的 200 健康检查计划。"""

    logger.info("使用占位 planner 生成 API 测试计划 (target=%s)", target)

    case = ApiTestCase(
        name="basic-health-check",
        description="基础连通性检查：期望返回 200",
        method="GET",
        url=target,
        validations=[
            ValidationRule(type="status_code", expected=200, op="eq"),
        ],
    )

    return ApiTestPlan(
        target=target,
        requirements=requirements or "基础连通性检查",
        base_url=base_url,
        cases=[case],
    )


def _extract_json(text: str) -> Dict[str, Any] | None:
    """从 LLM 返回的文本中尽力提取 JSON 对象。"""

    text = text.strip()
    # 1) 尝试直接解析
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) 尝试 ```json ... ``` 代码块
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        snippet = m.group(1)
        try:
            return json.loads(snippet)
        except Exception:
            pass

    # 3) 尝试第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            pass

    return None


def _build_plan_from_data(
    *, target: str, requirements: str, base_url: str | None, data: Dict[str, Any]
) -> ApiTestPlan | None:
    """根据 LLM 返回的 JSON 数据构造 ApiTestPlan。"""

    try:
        raw_base_url = data.get("base_url") or base_url
        cases_data = data.get("cases") or []
        cases: list[ApiTestCase] = []

        for idx, c in enumerate(cases_data, start=1):
            name = c.get("name") or f"case-{idx}"
            description = c.get("description") or None
            method = (c.get("method") or "GET").upper()
            url = c.get("url") or target
            headers = c.get("headers") or {}
            query = c.get("query") or {}
            body = c.get("body") if "body" in c else None

            validations_data = c.get("validations") or []
            validations: list[ValidationRule] = []
            for v in validations_data:
                try:
                    validations.append(
                        ValidationRule(
                            type=v.get("type") or "status_code",
                            path=v.get("path"),
                            expected=v.get("expected"),
                            op=v.get("op") or "eq",
                        )
                    )
                except Exception as ve:  # noqa: BLE001
                    logger.warning("忽略无效验证规则: %s", ve)

            cases.append(
                ApiTestCase(
                    name=name,
                    description=description,
                    method=method,  # type: ignore[arg-type]
                    url=url,
                    headers=headers,
                    query=query,
                    body=body,
                    validations=validations,
                )
            )

        if not cases:
            return None

        return ApiTestPlan(
            target=target,
            requirements=requirements or data.get("requirements", ""),
            base_url=raw_base_url,
            cases=cases,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("从 JSON 构造 ApiTestPlan 失败: %s", e)
        return None


async def plan_api_tests_with_llm(
    *, target: str, requirements: str, base_url: str | None = None
) -> ApiTestPlan:
    """调用本地 daoyou_agent 生成 API 测试计划。

    - 若 daoyou_agent 不可用或解析失败，则回退到简单健康检查计划。
    """

    if _controller is None or CognitiveRequest is None:  # type: ignore[truthy-function]
        return _fallback_plan(target, requirements, base_url)

    # 从环境变量读取与 Daoyou/memRag 集成相关的配置
    project_id = os.getenv("DAOYOU_PROJECT_ID", "autotest")
    user_id = os.getenv("DAOYOU_USER_ID", "autotest-user")
    user_api_key = os.getenv("DAOYOU_API_KEY") or None

    # 为 autotest 规划器构造一个稳定的 session_id，便于记忆按目标接口归档
    session_id = f"autotest:{target}"

    prompt = f"""你现在是一个 API 自动化测试规划助手。

目标接口或服务: {target}
测试需求: {requirements}

请根据以上信息，设计一份 API 测试计划，并严格按下述 JSON 结构输出（不要任何解释性文字）：

{{
  "base_url": "可选，字符串，留空则用每个 case.url 作为完整地址",
  "cases": [
    {{
      "name": "用例名称",
      "description": "可选，用例说明",
      "method": "GET/POST/PUT/DELETE 等",
      "url": "接口路径或完整 URL",
      "headers": {{"Content-Type": "application/json"}},
      "query": {{"q": "keyword"}},
      "body": {{"foo": "bar"}},
      "validations": [
        {{
          "type": "status_code" | "json_field" | "contains" | "header",
          "path": "对于 json_field/header 时的字段路径，如 data.code 或 X-Trace-Id",
          "expected": "期望值（任意 JSON 可序列化类型）",
          "op": "eq" | "ne" | "contains" | "not_contains"
        }}
      ]
    }}
  ]
}}

要求：
- 至少生成 1 条测试用例；
- 尽量覆盖正常场景和至少 1 个异常/边界场景；
- 严格返回 JSON，且字段名与上述示例完全一致。
"""

    try:
        req = CognitiveRequest(
            input=prompt,
            user_id=user_id,
            session_id=session_id,
            project_id=project_id,
            agent_id="autotest_planner",
            stream=False,
            # autotest 只需要规划，不做多轮意图编排
            enable_intent=False,
            # 开启记忆与知识库检索，让测试规划能够利用以往记录与知识库
            enable_memory=True,
            memory_depth=20,
            rag_level=1,
            enable_tools=False,
            # 允许学习闭环，将本次规划与上下文记录到 memRag
            enable_learning=True,
            context=None,
        )

        resp = await _controller.process_request(
            req,
            user_api_key=user_api_key,
            user_project_id=project_id,
        )

        raw = resp.content or ""
        data = _extract_json(raw)
        if not isinstance(data, dict):
            logger.warning("LLM 返回内容无法解析为 JSON，回退到占位计划")
            return _fallback_plan(target, requirements, base_url)

        plan = _build_plan_from_data(
            target=target,
            requirements=requirements,
            base_url=base_url,
            data=data,
        )
        if plan is None:
            logger.warning("从 LLM JSON 构造测试计划失败，回退到占位计划")
            return _fallback_plan(target, requirements, base_url)

        logger.info(
            "使用 daoyou_agent 规划出 %d 条 API 测试用例 (target=%s)",
            len(plan.cases),
            target,
        )
        return plan
    except Exception as e:  # noqa: BLE001
        logger.warning("调用 daoyou_agent 生成测试计划失败，回退到占位计划: %s", e)
        return _fallback_plan(target, requirements, base_url)
