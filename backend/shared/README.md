# memRagAgent - Shared 模块

跨服务共享的基础设施模块。

## 模块列表

### 1. vector_store.py - ChromaDB 向量存储

统一的向量存储接口，供 Memory 和 Knowledge 服务使用。

```python
from shared.vector_store import get_vector_store, SearchResult

# 获取单例
store = get_vector_store()

# 添加向量
store.upsert_vectors(
    collection_name="memories_PROJECTID",
    ids=["mem_1", "mem_2"],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    documents=["文本1", "文本2"],
    metadatas=[{"type": "semantic"}, {"type": "episodic"}],
)

# 搜索
results = store.search(
    collection_name="memories_PROJECTID",
    query_embedding=[0.1, 0.2, ...],
    top_k=10,
    where={"type": {"$in": ["semantic", "episodic"]}},
)
```

**配置**:
```bash
USE_CHROMADB=true
CHROMA_PERSIST_DIR=./chroma_data
# CHROMA_HOST=  # 远程模式
# CHROMA_PORT=8000
```

### 2. cache.py - Redis 缓存

统一的缓存接口，支持热点数据缓存。

```python
from shared.cache import get_cache_service, cached

# 获取单例
cache = get_cache_service()

# Profile 缓存
cache.set_profile(user_id, project_id, profile_dict)
profile = cache.get_profile(user_id, project_id)
cache.invalidate_profile(user_id)

# Embedding 缓存
cache.set_embedding(text_hash, embedding_list)
embedding = cache.get_embedding(text_hash)

# RAG 结果缓存
cache.set_rag(query_hash, project_id, results)
results = cache.get_rag(query_hash, project_id)

# 图谱查询缓存
cache.set_graph(query_hash, result_dict)
result = cache.get_graph(query_hash)

# 装饰器用法
@cached("profile", ttl=600)
def get_user_profile(user_id, project_id):
    ...
```

**配置**:
```bash
REDIS_URL=redis://:password@localhost:6379
REDIS_ENABLED=true
REDIS_CACHE_TTL=300
```

**TTL 设置**:
| 缓存类型 | TTL | 说明 |
|----------|-----|------|
| Profile | 10 min | 用户画像 |
| RAG | 5 min | RAG 检索结果 |
| Embedding | 1 hour | 向量嵌入 |
| Graph | 10 min | 图谱查询 |

## 使用方式

```python
import sys
from pathlib import Path

# 添加 shared 模块路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from shared import (
    get_vector_store,
    get_cache_service,
    SearchResult,
    cached,
)
```

## 依赖

```
chromadb>=0.4.22
redis>=5.0.0
```
