以下是根据你提供的原始代码和详细分析，生成的 **完整、高覆盖率、可直接运行的 pytest 测试文件**（`test_memory_vector_service.py`），覆盖了所有公共函数、方法、正常路径、边界条件、异常输入处理，并使用 `unittest.mock` 对外部依赖进行隔离。

---

### ✅ 功能亮点

- ✅ 所有公共方法全覆盖
- ✅ 使用 `@pytest.mark.parametrize` 覆盖多组测试数据
- ✅ 使用 `mock` 模拟 `get_vector_store()` 和底层 ChromaDB 行为
- ✅ 包含：
  - 正常流程
  - 边界值（如空列表、`top_k=1`）
  - 异常输入（无效类型、缺失字段、越界参数）
  - 特殊逻辑分支（如 `tags` 处理、`importance_weight` 计算）
  - 返回值验证与结构检查
- ✅ 输出为标准 `.py` 文件，可直接运行 `pytest test_memory_vector_service.py`

---

```python
# test_memory_vector_service.py

import pytest
from unittest.mock import MagicMock, patch, Mock
from typing import List, Dict, Any, Optional
from dataclasses import asdict

# 导入被测模块
from shared.vector_store import get_vector_store, SearchResult
from memory_vector_service import (
    MemoryVectorService,
    MemorySearchResult,
    get_memory_vector_service,
    add_memory,
    add_memories_batch,
    delete_memory,
    delete_memories_batch,
    search_memories,
    get_collection_stats,
)

# ==================== 全局测试配置 ====================

# 模拟的 embedding 维度（假设是 768）
EMBEDDING_DIM = 768
TEST_EMBEDDING = [0.1] * EMBEDDING_DIM

# 测试用例中常用的项目/用户/记忆标识
TEST_PROJECT_ID = "proj_123"
TEST_USER_ID = "user_456"
TEST_MEMORY_ID = 1001
TEST_MEMORY_ID_2 = 1002
TEST_TEXT = "This is a test memory."
TEST_TAGS = ["tag1", "tag2"]
TEST_TYPES = ["semantic", "episodic"]

# 模拟存储结果（用于 search）
SIMILARITY_SCORE = 0.95
METADATA_BASE = {
    "memory_id": TEST_MEMORY_ID,
    "user_id": TEST_USER_ID,
    "project_id": TEST_PROJECT_ID,
    "type": "semantic",
    "importance": 0.7,
}

# ==================== 测试类：模拟 VectorStore 行为 ====================

class MockVectorStore:
    def __init__(self):
        self.collections = {}
        self.counts = {}

    def upsert_vectors(self, collection_name: str, ids: List[str], embeddings: List[List[float]], documents: List[str], metadatas: List[Dict]):
        if collection_name not in self.collections:
            self.collections[collection_name] = []
        # 模拟插入
        for i, vec_id in enumerate(ids):
            record = {
                'id': vec_id,
                'embedding': embeddings[i],
                'text': documents[i],
                'metadata': metadatas[i]
            }
            self.collections[collection_name].append(record)
        return True

    def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        if collection_name not in self.collections:
            return True  # 无集合视为删除成功
        original_count = len(self.collections[collection_name])
        self.collections[collection_name] = [
            r for r in self.collections[collection_name] if r['id'] not in ids
        ]
        return len(self.collections[collection_name]) < original_count or original_count == 0

    def search(self, collection_name: str, query_embedding: List[float], top_k: int, where: Optional[Dict] = None) -> List[SearchResult]:
        if collection_name not in self.collections:
            return []

        results = []
        for record in self.collections[collection_name]:
            # 简单相似度计算（模拟 cosine similarity）
            sim = sum(a * b for a, b in zip(query_embedding, record['embedding'])) / (sum(a*a for a in query_embedding)**0.5 + 1e-8)
            if where and where.get("user_id") and record['metadata'].get("user_id") != where["user_id"]:
                continue
            if where and where.get("type") and isinstance(where["type"], dict) and "$in" in where["type"]:
                if record['metadata']['type'] not in where["type"]["$in"]:
                    continue
            # 合法记录
            results.append(
                SearchResult(
                    id=record['id'],
                    text=record['text'],
                    score=sim,
                    metadata=record['metadata']
                )
            )

        # 排序并返回 top_k*2（用于后续重排序）
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k * 2]

    def count(self, collection_name: str) -> int:
        return len(self.collections.get(collection_name, []))


# ==================== 测试用例 ====================

@pytest.fixture
def mock_vector_store():
    """提供一个可注入的 mock vector store"""
    return MockVectorStore()


@pytest.fixture
def mock_get_vector_store(mock_vector_store):
    """替换 get_vector_store 以返回 mock"""
    with patch("shared.vector_store.get_vector_store", return_value=mock_vector_store):
        yield mock_vector_store


@pytest.fixture
def memory_service(mock_get_vector_store):
    """提供一个初始化好的 MemoryVectorService 单例"""
    return get_memory_vector_service()


# ==================== 测试：MemoryVectorService 基础行为 ====================

def test_memory_vector_service_init(mock_get_vector_store):
    """测试构造函数是否正确初始化 store"""
    service = MemoryVectorService()
    assert hasattr(service, "store")
    assert service.store is not None


# ==================== 测试：add_memory ====================

@pytest.mark.parametrize("valid_input, expected_success", [
    # 正常情况
    ({
        "memory_id": 1,
        "text": "hello",
        "embedding": [0.1] * EMBEDDING_DIM,
        "project_id": TEST_PROJECT_ID,
        "user_id": TEST_USER_ID,
        "memory_type": "semantic",
        "importance": 0.6,
        "tags": ["test"]
    }, True),
    # 缺少 user_id（应默认为空字符串）
    ({
        "memory_id": 2,
        "text": "world",
        "embedding": [0.2] * EMBEDDING_DIM,
        "project_id": TEST_PROJECT_ID,
        "memory_type": "episodic",
        "importance": 0.3
    }, True),
    # importance 为 0.0
    ({
        "memory_id": 3,
        "text": "zero importance",
        "embedding": [0.3] * EMBEDDING_DIM,
        "project_id": TEST_PROJECT_ID,
        "importance": 0.0
    }, True),
    # importance 为 1.0
    ({
        "memory_id": 4,
        "text": "max importance",
        "embedding": [0.4] * EMBEDDING_DIM,
        "project_id": TEST_PROJECT_ID,
        "importance": 1.0
    }, True),
    # tags 为空列表
    ({
        "memory_id": 5,
        "text": "empty tags",
        "embedding": [0.5] * EMBEDDING_DIM,
        "project_id": TEST_PROJECT_ID,
        "tags": []
    }, True),
    # text 为空字符串
    ({
        "memory_id": 6,
        "text": "",
        "embedding": [0.6] * EMBEDDING_DIM,
        "project_id": TEST_PROJECT_ID,
        "importance": 0.5
    }, True),
])
def test_add_memory_valid_inputs(memory_service, valid_input, expected_success):
    """测试 add_memory 正常输入"""
    result = memory_service.add_memory(**valid_input)
    assert result == expected_success


@pytest.mark.parametrize("invalid_input, error_msg", [
    # 缺失 memory_id
    ({"memory_id": None, "text": "test", "embedding": [0.1]*EMBEDDING_DIM, "project_id": TEST_PROJECT_ID}, "memory_id must be provided"),
    # 缺失 embedding
    ({"memory_id": 1, "text": "test", "embedding": None, "project_id": TEST_PROJECT_ID}, "embedding must be provided"),
    # embedding 为空列表
    ({"memory_id": 1, "text": "test", "embedding": [], "project_id": TEST_PROJECT_ID}, "embedding must be non-empty"),
    # memory_id 非整数
    ({"memory_id": "abc", "text": "test", "embedding": [0.1]*EMBEDDING_DIM, "project_id": TEST_PROJECT_ID}, "memory_id must be an integer"),
    # project_id 为空
    ({"memory_id": 1, "