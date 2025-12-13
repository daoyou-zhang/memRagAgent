"""ChromaDB 向量存储服务

统一的向量存储接口，供 memory 和 knowledge 服务使用。
支持：
- 向量存储与检索
- 多集合管理
- 元数据过滤
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings

from dotenv import load_dotenv

# 加载配置
_backend_root = Path(__file__).parent.parent
load_dotenv(_backend_root / ".env")

# ChromaDB 配置
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(_backend_root / "chroma_data"))
CHROMA_HOST = os.getenv("CHROMA_HOST", "")  # 空则使用本地持久化
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))


@dataclass
class SearchResult:
    """向量检索结果"""
    id: str
    text: str
    score: float  # 相似度分数 (0-1，越高越相似)
    metadata: Dict[str, Any]


class VectorStore:
    """ChromaDB 向量存储客户端"""
    
    _instance: Optional["VectorStore"] = None
    
    def __init__(self):
        if CHROMA_HOST:
            # 连接远程 ChromaDB 服务
            self.client = chromadb.HttpClient(
                host=CHROMA_HOST,
                port=CHROMA_PORT,
            )
        else:
            # 本地持久化模式
            Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIR,
                settings=Settings(anonymized_telemetry=False),
            )
    
    @classmethod
    def get_instance(cls) -> "VectorStore":
        """单例模式获取实例"""
        if cls._instance is None:
            cls._instance = VectorStore()
        return cls._instance
    
    def get_or_create_collection(self, name: str, metadata: Dict = None) -> chromadb.Collection:
        """获取或创建集合"""
        return self.client.get_or_create_collection(
            name=name,
            metadata=metadata or {},
        )
    
    def delete_collection(self, name: str) -> bool:
        """删除集合"""
        try:
            self.client.delete_collection(name)
            return True
        except Exception:
            return False
    
    def add_vectors(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]] = None,
    ) -> bool:
        """批量添加向量"""
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas or [{}] * len(ids),
            )
            return True
        except Exception as e:
            print(f"[VectorStore] add_vectors error: {e}")
            return False
    
    def upsert_vectors(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]] = None,
    ) -> bool:
        """批量更新或插入向量"""
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas or [{}] * len(ids),
            )
            return True
        except Exception as e:
            print(f"[VectorStore] upsert_vectors error: {e}")
            return False
    
    def delete_vectors(
        self,
        collection_name: str,
        ids: List[str] = None,
        where: Dict = None,
    ) -> bool:
        """删除向量"""
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.delete(ids=ids, where=where)
            return True
        except Exception as e:
            print(f"[VectorStore] delete_vectors error: {e}")
            return False
    
    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        where: Dict = None,
        where_document: Dict = None,
    ) -> List[SearchResult]:
        """向量相似度检索
        
        Args:
            collection_name: 集合名称
            query_embedding: 查询向量
            top_k: 返回数量
            where: 元数据过滤条件，如 {"user_id": "xxx", "type": {"$in": ["semantic", "episodic"]}}
            where_document: 文档内容过滤
        
        Returns:
            SearchResult 列表，按相似度降序
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"],
            )
            
            search_results = []
            if results and results["ids"] and results["ids"][0]:
                ids = results["ids"][0]
                documents = results["documents"][0] if results["documents"] else [""] * len(ids)
                metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
                distances = results["distances"][0] if results["distances"] else [0] * len(ids)
                
                for i, doc_id in enumerate(ids):
                    # ChromaDB 返回的是距离，转换为相似度 (1 - distance/2 for cosine)
                    # 对于 L2 距离，使用 1 / (1 + distance)
                    distance = distances[i]
                    score = 1 / (1 + distance)  # 转换为 0-1 相似度
                    
                    search_results.append(SearchResult(
                        id=doc_id,
                        text=documents[i],
                        score=score,
                        metadata=metadatas[i],
                    ))
            
            return search_results
            
        except Exception as e:
            print(f"[VectorStore] search error: {e}")
            return []
    
    def get_by_ids(
        self,
        collection_name: str,
        ids: List[str],
    ) -> List[Dict]:
        """根据 ID 获取向量"""
        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.get(
                ids=ids,
                include=["documents", "metadatas", "embeddings"],
            )
            
            items = []
            if results and results["ids"]:
                for i, doc_id in enumerate(results["ids"]):
                    items.append({
                        "id": doc_id,
                        "document": results["documents"][i] if results["documents"] else "",
                        "metadata": results["metadatas"][i] if results["metadatas"] else {},
                        "embedding": results["embeddings"][i] if results["embeddings"] else None,
                    })
            return items
        except Exception:
            return []
    
    def count(self, collection_name: str) -> int:
        """获取集合中的向量数量"""
        try:
            collection = self.get_or_create_collection(collection_name)
            return collection.count()
        except Exception:
            return 0


# 便捷函数
def get_vector_store() -> VectorStore:
    """获取 VectorStore 单例"""
    return VectorStore.get_instance()


# 集合命名规范
def get_memory_collection_name(project_id: str) -> str:
    """获取记忆集合名称"""
    return f"memories_{project_id}" if project_id else "memories_default"


def get_knowledge_collection_name(domain: str, project_id: str = None) -> str:
    """获取知识库集合名称"""
    base = f"knowledge_{domain}"
    return f"{base}_{project_id}" if project_id else base
