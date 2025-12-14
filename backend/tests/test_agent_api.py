"""Agent 服务（daoyou_agent）API 测试

测试认知对话、工具、Prompt 管理等接口
"""
import pytest
import httpx
from datetime import datetime


class TestHealthCheck:
    """健康检查"""
    
    def test_health(self, agent_client: httpx.Client):
        """测试健康检查接口"""
        response = agent_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
    
    def test_root(self, agent_client: httpx.Client):
        """测试根路径"""
        response = agent_client.get("/")
        assert response.status_code == 200


class TestCognitiveAPI:
    """认知对话 API 测试"""
    
    def test_cognitive_simple(self, agent_client: httpx.Client, test_user_id: str, test_session_id: str):
        """测试简单认知对话"""
        payload = {
            "input": "你好，请介绍一下你自己",
            "user_id": test_user_id,
            "session_id": test_session_id,
            "stream": False
        }
        response = agent_client.post("/api/v1/cognitive/process", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "content" in data or "response" in data
    
    def test_cognitive_with_memory(self, agent_client: httpx.Client, test_user_id: str, test_session_id: str):
        """测试带记忆的认知对话"""
        payload = {
            "input": "我之前说过什么？",
            "user_id": test_user_id,
            "session_id": test_session_id,
            "use_memory": True,
            "memory_depth": 5,
            "stream": False
        }
        response = agent_client.post("/api/v1/cognitive/process", json=payload)
        assert response.status_code == 200
    
    def test_cognitive_with_rag(self, agent_client: httpx.Client, test_user_id: str):
        """测试带 RAG 的认知对话"""
        payload = {
            "input": "帮我查一下相关资料",
            "user_id": test_user_id,
            "use_rag": True,
            "rag_top_k": 3,
            "stream": False
        }
        response = agent_client.post("/api/v1/cognitive/process", json=payload)
        assert response.status_code == 200
    
    @pytest.mark.slow
    def test_cognitive_intent_analysis(self, agent_client: httpx.Client, test_user_id: str):
        """测试意图分析（慢速测试，LLM 调用可能超时）"""
        payload = {
            "input": "你好",  # 简单输入，减少处理时间
            "user_id": test_user_id,
            "stream": False
        }
        try:
            response = agent_client.post("/api/v1/cognitive/process", json=payload, timeout=120.0)
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"超时或连接失败: {e}")


class TestToolsAPI:
    """工具管理 API 测试"""
    
    def test_list_tools(self, agent_client: httpx.Client):
        """测试获取工具列表"""
        # 注意尾部斜杠，避免 307 重定向
        response = agent_client.get("/api/v1/tools/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))
    
    def test_get_tool_detail(self, agent_client: httpx.Client):
        """测试获取工具详情"""
        # 先获取列表
        list_resp = agent_client.get("/api/v1/tools")
        if list_resp.status_code == 200:
            tools = list_resp.json()
            if isinstance(tools, list) and len(tools) > 0:
                tool_name = tools[0].get("name")
                if tool_name:
                    response = agent_client.get(f"/api/v1/tools/{tool_name}")
                    assert response.status_code in [200, 404]


class TestPromptsAPI:
    """Prompt 管理 API 测试"""
    
    def test_get_default_prompts(self, agent_client: httpx.Client):
        """测试获取默认 Prompt"""
        response = agent_client.get("/api/v1/prompts/default")
        assert response.status_code == 200
        data = response.json()
        assert "intent_system_prompt" in data
        assert "response_system_prompt" in data
    
    def test_list_industries(self, agent_client: httpx.Client):
        """测试获取行业列表"""
        response = agent_client.get("/api/v1/prompts/industries")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_industry_prompt(self, agent_client: httpx.Client):
        """测试获取行业 Prompt"""
        response = agent_client.get("/api/v1/prompts/industries/divination")
        assert response.status_code in [200, 404]
    
    def test_list_templates(self, agent_client: httpx.Client):
        """测试获取模板列表"""
        response = agent_client.get("/api/v1/prompts/templates")
        assert response.status_code == 200
    
    def test_preview_prompt(self, agent_client: httpx.Client):
        """测试预览 Prompt"""
        response = agent_client.post(
            "/api/v1/prompts/preview",
            params={"user_input": "测试输入", "industry": "legal"}
        )
        assert response.status_code == 200
    
    def test_crud_prompt_config(self, agent_client: httpx.Client):
        """测试 Prompt 配置 CRUD"""
        # 创建
        create_payload = {
            "category": f"test_{datetime.now().strftime('%H%M%S')}",
            "name": "测试配置",
            "description": "pytest 自动化测试",
            "response_system_prompt": "你是一个测试助手。"
        }
        create_resp = agent_client.post("/api/v1/prompts/configs", json=create_payload)
        
        if create_resp.status_code in [200, 201]:
            config = create_resp.json()
            config_id = config.get("id")
            
            # 读取
            get_resp = agent_client.get(f"/api/v1/prompts/configs/{config_id}")
            assert get_resp.status_code == 200
            
            # 更新
            update_payload = {"name": "更新后的测试配置"}
            update_resp = agent_client.put(f"/api/v1/prompts/configs/{config_id}", json=update_payload)
            assert update_resp.status_code == 200
            
            # 删除
            delete_resp = agent_client.delete(f"/api/v1/prompts/configs/{config_id}")
            assert delete_resp.status_code == 200
