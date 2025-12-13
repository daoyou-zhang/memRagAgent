"""Memory 向量服务

封装 ChromaDB 向量操作，提供记忆向量的存储和检索。
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 添加 shared 模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.vector_store import (
    get_vector_store,
    get_memory_collection_name,
    SearchResult,
)


@dataclass
class MemorySearchResult:
    """记忆检索结果"""
    memory_id: int
    text: str
    similarity: float
    importance: float
    score: float  # 综合得分
    memory_type: str
    metadata: Dict[str, Any]


class MemoryVectorService:
    """记忆向量服务"""
    
    def __init__(self):
        self.store = get_vector_store()
    
    def _get_collection_name(self, project_id: str) -> str:
        """获取集合名称"""
        return get_memory_collection_name(project_id)
    
    def _make_id(self, memory_id: int) -> str:
        """生成向量 ID"""
        return f"mem_{memory_id}"
    
    def _parse_id(self, vec_id: str) -> int:
        """解析记忆 ID"""
        return int(vec_id.replace("mem_", ""))
    
    def add_memory(
        self,
        memory_id: int,
        text: str,
        embedding: List[float],
        project_id: str,
        user_id: str = None,
        memory_type: str = "semantic",
        importance: float = 0.5,
        tags: List[str] = None,
    ) -> bool:
        """添加记忆向量"""
        collection_name = self._get_collection_name(project_id)
        vec_id = self._make_id(memory_id)
        
        metadata = {
            "memory_id": memory_id,
            "user_id": user_id or "",
            "project_id": project_id or "",
            "type": memory_type,
            "importance": importance,
        }
        if tags:
            metadata["tags"] = ",".join(tags)  # ChromaDB 不支持列表值
        
        return self.store.upsert_vectors(
            collection_name=collection_name,
            ids=[vec_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
    
    def add_memories_batch(
        self,
        memories: List[Dict[str, Any]],
        project_id: str,
    ) -> int:
        """批量添加记忆向量（性能优化）
        
        Args:
            memories: 记忆列表，每个元素包含：
                - memory_id: int
                - text: str
                - embedding: List[float]
                - user_id: str (可选)
                - memory_type: str (可选，默认 semantic)
                - importance: float (可选，默认 0.5)
                - tags: List[str] (可选)
            project_id: 项目 ID
        
        Returns:
            成功添加的数量
        """
        if not memories:
            return 0
        
        collection_name = self._get_collection_name(project_id)
        
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for mem in memories:
            memory_id = mem.get("memory_id")
            embedding = mem.get("embedding")
            text = mem.get("text", "")
            
            if not memory_id or not embedding:
                continue
            
            vec_id = self._make_id(memory_id)
            metadata = {
                "memory_id": memory_id,
                "user_id": mem.get("user_id", ""),
                "project_id": project_id,
                "type": mem.get("memory_type", "semantic"),
                "importance": mem.get("importance", 0.5),
            }
            if mem.get("tags"):
                metadata["tags"] = ",".join(mem["tags"])
            
            ids.append(vec_id)
            embeddings.append(embedding)
            documents.append(text)
            metadatas.append(metadata)
        
        if not ids:
            return 0
        
        success = self.store.upsert_vectors(
            collection_name=collection_name,
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        
        return len(ids) if success else 0
    
    def delete_memory(self, memory_id: int, project_id: str) -> bool:
        """删除记忆向量"""
        collection_name = self._get_collection_name(project_id)
        vec_id = self._make_id(memory_id)
        return self.store.delete_vectors(collection_name, ids=[vec_id])
    
    def delete_memories_batch(self, memory_ids: List[int], project_id: str) -> bool:
        """批量删除记忆向量"""
        collection_name = self._get_collection_name(project_id)
        vec_ids = [self._make_id(mid) for mid in memory_ids]
        return self.store.delete_vectors(collection_name, ids=vec_ids)
    
    def search_memories(
        self,
        query_embedding: List[float],
        project_id: str,
        user_id: str = None,
        memory_types: List[str] = None,
        top_k: int = 10,
        importance_weight: float = 0.2,
    ) -> List[MemorySearchResult]:
        """检索相关记忆
        
        Args:
            query_embedding: 查询向量
            project_id: 项目 ID
            user_id: 用户 ID（可选过滤）
            memory_types: 记忆类型过滤，如 ["semantic", "episodic"]
            top_k: 返回数量
            importance_weight: 重要性权重，综合得分 = 相似度 * (1-w) + 重要性 * w
        
        Returns:
            MemorySearchResult 列表
        """
        collection_name = self._get_collection_name(project_id)
        
        # 构建过滤条件
        where = {}
        if user_id:
            where["user_id"] = user_id
        if memory_types:
            where["type"] = {"$in": memory_types}
        
        # 执行向量检索
        results = self.store.search(
            collection_name=collection_name,
            query_embedding=query_embedding,
            top_k=top_k * 2,  # 多取一些，后面重排序
            where=where if where else None,
        )
        
        # 转换并计算综合得分
        memory_results = []
        for r in results:
            importance = float(r.metadata.get("importance", 0.5))
            similarity = r.score
            
            # 综合得分
            final_score = similarity * (1 - importance_weight) + importance * importance_weight
            
            memory_results.append(MemorySearchResult(
                memory_id=r.metadata.get("memory_id", self._parse_id(r.id)),
                text=r.text,
                similarity=similarity,
                importance=importance,
                score=final_score,
                memory_type=r.metadata.get("type", "unknown"),
                metadata=r.metadata,
            ))
        
        # 按综合得分排序
        memory_results.sort(key=lambda x: x.score, reverse=True)
        
        return memory_results[:top_k]
    
    def get_collection_stats(self, project_id: str) -> Dict[str, Any]:
        """获取集合统计信息"""
        collection_name = self._get_collection_name(project_id)
        count = self.store.count(collection_name)
        return {
            "collection_name": collection_name,
            "vector_count": count,
        }


# 单例
_memory_vector_service: Optional[MemoryVectorService] = None


def get_memory_vector_service() -> MemoryVectorService:
    """获取 MemoryVectorService 单例"""
    global _memory_vector_service
    if _memory_vector_service is None:
        _memory_vector_service = MemoryVectorService()
    return _memory_vector_service
