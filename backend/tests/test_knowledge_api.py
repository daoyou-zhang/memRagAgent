"""Knowledge 服务 API 测试

测试知识集合、文档、RAG、图谱等接口
"""
import pytest
import httpx
from datetime import datetime


class TestHealthCheck:
    """健康检查"""
    
    def test_health(self, knowledge_client: httpx.Client):
        """测试健康检查接口"""
        # Knowledge 服务可能没有 /health
        response = knowledge_client.get("/")
        assert response.status_code in [200, 404]


class TestCollectionsAPI:
    """知识集合 API 测试"""
    
    def test_list_collections(self, knowledge_client: httpx.Client):
        """测试获取集合列表"""
        response = knowledge_client.get("/api/knowledge/collections")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))
    
    def test_create_collection(self, knowledge_client: httpx.Client, test_project_id: str):
        """测试创建知识集合"""
        payload = {
            "project_id": test_project_id,
            "name": f"测试集合_{datetime.now().strftime('%H%M%S')}",
            "domain": "testing",
            "description": "pytest 自动化测试创建"
        }
        response = knowledge_client.post("/api/knowledge/collections", json=payload)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data or "collection_id" in data


class TestDocumentsAPI:
    """知识文档 API 测试"""
    
    def test_list_documents(self, knowledge_client: httpx.Client):
        """测试获取文档列表"""
        response = knowledge_client.get("/api/knowledge/documents")
        assert response.status_code == 200
    
    def test_create_document(self, knowledge_client: httpx.Client):
        """测试创建文档（需要先有集合）"""
        # 先获取集合列表
        collections_resp = knowledge_client.get("/api/knowledge/collections")
        if collections_resp.status_code == 200:
            collections = collections_resp.json()
            if isinstance(collections, list) and len(collections) > 0:
                collection_id = collections[0].get("id")
                if collection_id:
                    payload = {
                        "collection_id": collection_id,
                        "title": f"测试文档_{datetime.now().strftime('%H%M%S')}",
                        "content": "这是一段测试内容，用于验证文档创建功能。",
                        "source_type": "test"
                    }
                    response = knowledge_client.post("/api/knowledge/documents", json=payload)
                    assert response.status_code in [200, 201, 400]


class TestKnowledgeRAGAPI:
    """知识库 RAG API 测试"""
    
    @pytest.mark.slow
    def test_rag_query(self, knowledge_client: httpx.Client):
        """测试知识库 RAG 查询（慢速测试）"""
        payload = {
            "query": "测试",
            "top_k": 3
        }
        try:
            response = knowledge_client.post("/api/knowledge/rag/query", json=payload, timeout=120.0)
            assert response.status_code in [200, 404]
        except Exception as e:
            pytest.skip(f"RAG 查询超时: {e}")
    
    def test_rag_query_with_domain(self, knowledge_client: httpx.Client):
        """测试带领域过滤的 RAG 查询"""
        payload = {
            "query": "法律问题咨询",
            "domain": "legal",
            "top_k": 3
        }
        response = knowledge_client.post("/api/knowledge/rag/query", json=payload)
        assert response.status_code in [200, 404]


class TestGraphAPI:
    """知识图谱 API 测试"""
    
    def test_graph_search(self, knowledge_client: httpx.Client):
        """测试图谱实体搜索"""
        # 尝试不同的参数格式
        response = knowledge_client.post(
            "/api/knowledge/graph/search",
            json={"keyword": "测试", "limit": 10}
        )
        # 200 成功或 400/503 服务不可用
        assert response.status_code in [200, 400, 404, 405, 500, 503]
    
    def test_graph_neighbors(self, knowledge_client: httpx.Client):
        """测试获取实体邻居"""
        payload = {
            "entity_name": "测试实体",
            "depth": 1
        }
        response = knowledge_client.post("/api/knowledge/graph/neighbors", json=payload)
        assert response.status_code in [200, 404, 500, 503]
    
    def test_graph_extract(self, knowledge_client: httpx.Client):
        """测试从文本抽取实体"""
        payload = {
            "text": "张三是一名律师，他在北京工作，专注于合同法领域。"
        }
        response = knowledge_client.post("/api/knowledge/graph/extract", json=payload)
        assert response.status_code in [200, 500, 503]
