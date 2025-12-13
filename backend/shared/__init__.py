"""Shared utilities for memRagAgent backend services"""
from .vector_store import (
    VectorStore,
    get_vector_store,
    SearchResult,
    get_memory_collection_name,
    get_knowledge_collection_name,
)
from .cache import (
    CacheService,
    get_cache_service,
    get_redis_client,
    cached,
)

__all__ = [
    # Vector Store
    "VectorStore",
    "get_vector_store",
    "SearchResult",
    "get_memory_collection_name",
    "get_knowledge_collection_name",
    # Cache
    "CacheService",
    "get_cache_service",
    "get_redis_client",
    "cached",
]
