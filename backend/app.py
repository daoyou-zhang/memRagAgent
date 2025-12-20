from daoyou.app.main import app  # 统一对外暴露道友的 FastAPI 应用
from memRagAgent.backend.daoyou_agent.api import cognitive as memrag_cognitive
from memRagAgent.backend.daoyou_agent.api import tools as memrag_tools
from memRagAgent.backend.daoyou_agent.api import prompts as memrag_prompts

# memRagAgent 的 API 作为“弱接口”挂载在同一服务下，方便前期联调和测试。
# 核心认知路径仍然通过内部 service 调用 CognitiveController；
# 这些 /memrag/* 路由未来若不再需要，可以直接下线，不影响主业务。

app.include_router(memrag_cognitive.router, prefix="/memrag/cognitive", tags=["memrag-cognitive"])
app.include_router(memrag_tools.router, prefix="/memrag/tools", tags=["memrag-tools"])
app.include_router(memrag_prompts.router, prefix="/memrag/prompts", tags=["memrag-prompts"])
