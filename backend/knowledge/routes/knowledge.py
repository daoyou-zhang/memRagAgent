from __future__ import annotations

import os
import sys
import math
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from flask import Blueprint, jsonify, request, g
from loguru import logger
from sqlalchemy.orm import Session

# 添加 shared 模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.auth import flask_auth_required, apply_project_filter, Scopes
from ..repository.db_session import SessionLocal
from ..models.knowledge import KnowledgeCollection, KnowledgeDocument, KnowledgeChunk
from ..processing.text_processing import TextProcessor
from ..processing.embedding_processing import generate_embeddings_batch

knowledge_bp = Blueprint("knowledge", __name__)


def _get_cache_service():
    """获取缓存服务（失败返回 None）"""
    try:
        from shared.cache import get_cache_service
        return get_cache_service()
    except Exception:
        return None


def _knowledge_query_hash(query: str, project_id: str = None, domain: str = None) -> str:
    """生成知识库查询哈希"""
    key = f"kn:{query}:{project_id or ''}:{domain or ''}"
    return hashlib.md5(key.encode()).hexdigest()[:16]

from .graph import graph_bp  # noqa: E402

knowledge_bp.register_blueprint(graph_bp, url_prefix="/graph")


def to_beijing_iso(dt: datetime | None) -> str | None:
    """将时间统一转换为北京时间字符串，用于 API 返回。"""

    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("Asia/Shanghai")).isoformat()


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _match_required_tags(chunk_tags: list[str] | None, required: list[str] | None) -> bool:
    """检查 chunk 是否满足必选标签要求。

    - 若 required 为空或 None，则一律通过；
    - 若 required 有值但 chunk_tags 为空，则不通过；
    - 否则要求 required 是 chunk_tags 的子集。
    """

    if not required:
        return True
    if not chunk_tags:
        return False
    return set(required).issubset(set(chunk_tags))


def _count_preferred_overlap(chunk_tags: list[str] | None, preferred: list[str] | None) -> int:
    """统计 chunk 标签与期望标签的交集个数。

    preferred 为空时返回 0。
    """

    if not preferred or not chunk_tags:
        return 0
    return len(set(chunk_tags) & set(preferred))


@knowledge_bp.get("/health")
def health() -> tuple[object, int]:
    return jsonify({"status": "ok", "service": "knowledge", "version": "0.1"}), 200


@knowledge_bp.post("/collections")
@flask_auth_required(scopes=[Scopes.WRITE_KNOWLEDGE])
def create_collection():
    payload = request.get_json(force=True) or {}

    name = (payload.get("name") or "").strip()
    domain = (payload.get("domain") or "").strip()
    if not name or not domain:
        return jsonify({"error": "fields 'name' and 'domain' are required"}), 400

    project_id = payload.get("project_id")
    description = payload.get("description")
    default_language = payload.get("default_language")
    metadata = payload.get("metadata")

    db: Session = SessionLocal()
    try:
        col = KnowledgeCollection(
            project_id=project_id,
            name=name,
            domain=domain,
            description=description,
            default_language=default_language,
            extra_metadata=metadata,
        )
        db.add(col)
        db.commit()
        db.refresh(col)

        return (
            jsonify(
                {
                    "id": col.id,
                    "project_id": col.project_id,
                    "name": col.name,
                    "domain": col.domain,
                    "description": col.description,
                    "default_language": col.default_language,
                    "metadata": col.extra_metadata,
                    "created_at": to_beijing_iso(col.created_at),
                    "updated_at": to_beijing_iso(col.updated_at),
                }
            ),
            201,
        )
    finally:
        db.close()


@knowledge_bp.get("/collections")
@flask_auth_required(scopes=[Scopes.READ_KNOWLEDGE])
def list_collections():
    domain = request.args.get("domain")

    db: Session = SessionLocal()
    try:
        q = db.query(KnowledgeCollection)
        
        # 应用租户隔离
        q = apply_project_filter(q, KnowledgeCollection)
                
        if domain:
            q = q.filter(KnowledgeCollection.domain == domain)

        items = []
        for col in q.order_by(KnowledgeCollection.created_at.desc()).all():
            items.append(
                {
                    "id": col.id,
                    "project_id": col.project_id,
                    "name": col.name,
                    "domain": col.domain,
                    "description": col.description,
                    "default_language": col.default_language,
                    "metadata": col.extra_metadata,
                    "created_at": col.created_at.isoformat(),
                    "updated_at": col.updated_at.isoformat(),
                }
            )

        return jsonify({"items": items})
    finally:
        db.close()


@knowledge_bp.delete("/documents/<int:document_id>")
@flask_auth_required(scopes=[Scopes.DELETE_KNOWLEDGE])
def delete_document(document_id: int):
    """物理删除单个文档及其所有 chunks。

    使用场景：
    - 源数据有误或需要完全替换时，先删除旧文档再重建；
    - 向量库与图谱都保留源数据，逻辑删除没有必要。
    """

    db: Session = SessionLocal()
    try:
        # 关联 collection 以实现租户隔离检查
        q = db.query(KnowledgeDocument).join(
            KnowledgeCollection, KnowledgeDocument.collection_id == KnowledgeCollection.id
        ).filter(KnowledgeDocument.id == document_id)
        
        # 应用租户隔离
        q = apply_project_filter(q, KnowledgeCollection)
        
        doc = q.first()
        if not doc:
            return jsonify({"error": "document not found or access denied"}), 404

        # 先删除该文档下的所有 chunks
        deleted_chunks = (
            db.query(KnowledgeChunk)
            .filter(KnowledgeChunk.document_id == document_id)
            .delete(synchronize_session=False)
        )

        # 再删除文档本身
        db.delete(doc)
        db.commit()

        return jsonify({
            "document_id": document_id,
            "deleted_chunks": int(deleted_chunks),
            "status": "deleted",
        })
    finally:
        db.close()


@knowledge_bp.post("/collections/<int:collection_id>/reset")
@flask_auth_required(scopes=[Scopes.DELETE_KNOWLEDGE])
def reset_collection(collection_id: int):
    """清空指定集合下的所有文档及 chunks，保留集合记录本身。

    - 用于快速重建某个实验集合的数据；
    - 更大范围的批量清理（如按 project_id/domain）可以在数据库层面手动操作。
    """

    db: Session = SessionLocal()
    try:
        # 租户隔离检查
        q = db.query(KnowledgeCollection).filter(KnowledgeCollection.id == collection_id)
        q = apply_project_filter(q, KnowledgeCollection)
        
        col = q.first()
        if not col:
            return jsonify({"error": "collection not found or access denied"}), 404

        # 找出该集合下的所有文档 ID
        doc_ids = [
            row.id
            for row in db.query(KnowledgeDocument.id)
            .filter(KnowledgeDocument.collection_id == collection_id)
            .all()
        ]

        deleted_chunks = 0
        deleted_docs = 0

        if doc_ids:
            # 删除这些文档下的所有 chunks
            deleted_chunks = (
                db.query(KnowledgeChunk)
                .filter(KnowledgeChunk.document_id.in_(doc_ids))
                .delete(synchronize_session=False)
            )

            # 删除文档本身
            deleted_docs = (
                db.query(KnowledgeDocument)
                .filter(KnowledgeDocument.id.in_(doc_ids))
                .delete(synchronize_session=False)
            )

        db.commit()

        return jsonify({
            "collection_id": collection_id,
            "deleted_documents": int(deleted_docs),
            "deleted_chunks": int(deleted_chunks),
            "status": "reset_done",
        })
    finally:
        db.close()


@knowledge_bp.post("/rag/query")
@flask_auth_required(scopes=[Scopes.READ_KNOWLEDGE])
def knowledge_rag_query():
    """知识库 RAG 查询：基于 knowledge_chunks 的 embedding 做向量检索。

    请求体示例：

    {
      "project_id": "DAOYOUTEST",     // 可选
      "collection_ids": [1, 2],       // 可选
      "domain": "law",              // 可选
      "query": "解除劳动合同的补偿标准是什么？",  // 必填
      "top_k": 8
      "required_tags": ["劳动合同", "解除"],      // 可选：必须全部命中的标签
      "preferred_tags": ["经济补偿金"]           // 可选：命中越多，得分稍微加分
    }
    """

    payload = request.get_json(force=True) or {}

    project_id = payload.get("project_id")
    collection_ids = payload.get("collection_ids") or []
    domain = payload.get("domain")
    query_text = (payload.get("query") or "").strip()
    try:
        top_k = int(payload.get("top_k", 8))
    except (TypeError, ValueError):
        top_k = 8
    if top_k <= 0:
        top_k = 8
    if top_k > 50:
        top_k = 50

    if not query_text:
        return jsonify({"error": "field 'query' is required"}), 400

    # 尝试从 Redis 缓存获取
    cache = _get_cache_service()
    cache_key = _knowledge_query_hash(query_text, project_id, domain)
    if cache:
        cached_result = cache.get(f"memrag:krag:{cache_key}")
        if cached_result:
            logger.debug(f"[Knowledge RAG] Cache hit for query: {query_text[:30]}...")
            return jsonify({
                "used_chunks": cached_result,
                "debug": {"from_cache": True},
            })

    # tags 约束（可选）：
    # - required_tags：必须全部包含，若导致候选集为空会自动回退为不使用必选标签；
    # - preferred_tags：命中则在向量相似度基础上稍作加分，对无标签数据无任何影响。
    required_tags = payload.get("required_tags") or []
    preferred_tags = payload.get("preferred_tags") or []
    # 规范为字符串列表
    required_tags = [str(t).strip() for t in required_tags if str(t).strip()]
    preferred_tags = [str(t).strip() for t in preferred_tags if str(t).strip()]

    db: Session = SessionLocal()
    try:
        # 1) 选出候选 chunks
        q = db.query(KnowledgeChunk, KnowledgeDocument, KnowledgeCollection).join(
            KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id
        ).join(KnowledgeCollection, KnowledgeDocument.collection_id == KnowledgeCollection.id)

        # 应用租户隔离
        q = apply_project_filter(q, KnowledgeCollection)

        if collection_ids:
            q = q.filter(KnowledgeDocument.collection_id.in_(collection_ids))
        if domain:
            q = q.filter(KnowledgeCollection.domain == domain)

        # 为避免一次取太多，先限制最大候选数
        max_candidates = int(payload.get("max_candidates", 1000))
        raw_rows = q.limit(max_candidates).all()

        # 2) 为 query 生成 embedding
        try:
            q_emb_list = generate_embeddings_batch([query_text])
        except Exception as e:  # noqa: BLE001
            return (
                jsonify({"error": "failed to generate embedding", "detail": str(e)}),
                500,
            )
        if not q_emb_list or not q_emb_list[0]:
            return jsonify({"error": "empty query embedding"}), 500
        q_emb = [float(x) for x in q_emb_list[0]]

        # 3) 在应用层计算相似度 + importance + 可选 tags 加分
        # 先基于 required_tags 做一次软过滤：若过滤后为空，则退回到未过滤集合。
        base_rows = list(raw_rows)
        filtered_rows: list[tuple[KnowledgeChunk, KnowledgeDocument, KnowledgeCollection]] = []

        if required_tags:
            for ch, doc, col in base_rows:
                # chunk.tags 优先，其次从 extra_metadata.tags 里取
                c_tags = []
                if ch.tags:
                    c_tags = list(ch.tags)
                elif ch.extra_metadata and isinstance(ch.extra_metadata, dict):
                    meta_tags = ch.extra_metadata.get("tags")
                    if isinstance(meta_tags, list):
                        c_tags = [str(t) for t in meta_tags]
                if _match_required_tags(c_tags, required_tags):
                    filtered_rows.append((ch, doc, col))

        if not filtered_rows:
            # 若 required_tags 过滤结果为空，则忽略必选标签约束
            filtered_rows = base_rows

        candidates: list[dict] = []
        for ch, doc, col in filtered_rows:
            emb = ch.embedding or []
            try:
                vec = [float(x) for x in emb]
            except Exception:
                continue

            sim = _cosine(q_emb, vec)
            importance = float(ch.importance or 0.0)
            if importance < 0.0:
                importance = 0.0
            if importance > 1.0:
                importance = 1.0

            # tags 加权：命中 preferred_tags 越多，额外加一点小权重
            c_tags: list[str] = []
            if ch.tags:
                c_tags = list(ch.tags)
            elif ch.extra_metadata and isinstance(ch.extra_metadata, dict):
                meta_tags = ch.extra_metadata.get("tags")
                if isinstance(meta_tags, list):
                    c_tags = [str(t) for t in meta_tags]

            overlap_cnt = _count_preferred_overlap(c_tags, preferred_tags)
            tag_bonus = 0.02 * overlap_cnt

            final_score = sim * 0.8 + importance * 0.2 + tag_bonus

            candidates.append(
                {
                    "chunk": ch,
                    "doc": doc,
                    "col": col,
                    "similarity": float(sim),
                    "importance": float(importance),
                    "score": float(final_score),
                    "tag_bonus": float(tag_bonus),
                    "matched_tags": c_tags,
                }
            )

        candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = candidates[:top_k]

        used_chunks: list[dict] = []
        total_sim = 0.0
        total_score = 0.0
        for item in top_candidates:
            ch: KnowledgeChunk = item["chunk"]
            doc: KnowledgeDocument = item["doc"]
            col: KnowledgeCollection = item["col"]
            total_sim += float(item["similarity"])
            total_score += float(item["score"])

            used_chunks.append(
                {
                    "id": ch.id,
                    "document_id": ch.document_id,
                    "collection_id": doc.collection_id,
                    "collection_name": col.name,
                    "domain": col.domain,
                    "section_label": ch.section_label,
                    "text": ch.text,
                    "score": item["score"],
                    "similarity": item["similarity"],
                    "importance": item["importance"],
                    "metadata": ch.extra_metadata,
                }
            )

        debug_info = {
            "total_candidates": len(candidates),
            "top_k": top_k,
            "avg_similarity_top_k": total_sim / len(top_candidates) if top_candidates else 0.0,
            "avg_score_top_k": total_score / len(top_candidates) if top_candidates else 0.0,
            "from_cache": False,
        }

        # 写入缓存
        if cache and used_chunks:
            cache.set(f"memrag:krag:{cache_key}", used_chunks, 300)  # 5 min TTL
            logger.debug(f"[Knowledge RAG] Cached {len(used_chunks)} results")

        return jsonify({"used_chunks": used_chunks, "debug": debug_info})
    finally:
        db.close()


@knowledge_bp.post("/documents/<int:document_id>/index")
@flask_auth_required(scopes=[Scopes.WRITE_KNOWLEDGE])
def index_document(document_id: int):
    """为指定文档执行索引：读取 source_uri → 分块 → 生成向量 → 写入 knowledge_chunks。

    - 支持 JSONL / JSON 数组 / 其他文本类文件；
    - 每次索引会先删除该文档已有的 chunks 再重建；
    - 完成后将 document.status 标记为 indexed。
    """

    db: Session = SessionLocal()
    try:
        # 关联 collection 以实现租户隔离检查
        q = db.query(KnowledgeDocument).join(
            KnowledgeCollection, KnowledgeDocument.collection_id == KnowledgeCollection.id
        ).filter(KnowledgeDocument.id == document_id)
        
        # 应用租户隔离
        q = apply_project_filter(q, KnowledgeCollection)
        
        doc = q.first()
        if not doc:
            return jsonify({"error": "document not found or access denied"}), 404

        # 若当前已在索引中，则直接返回，避免重复触发
        if doc.status == "indexing":
            return jsonify({"error": "document is indexing"}), 409

        if not doc.source_uri:
            return jsonify({"error": "document.source_uri is missing"}), 400

        # 将状态先标记为 indexing
        doc.status = "indexing"
        db.commit()

        source = str(doc.source_uri)
        # 简单支持 file:/// 前缀或直接本地路径
        from pathlib import Path

        if source.startswith("file://"):
            path = Path(source[7:])
        else:
            path = Path(source)

        print(f"[knowledge.index] start document_id={document_id}, source={path}")

        if not path.exists() or not path.is_file():
            doc.status = "error"
            db.commit()
            return jsonify({"error": f"source file not found: {path}"}), 400

        tp = TextProcessor()

        ext = path.suffix.lower()
        all_chunks: list[str] = []
        per_chunk_meta: list[dict] = []

        try:
            if ext == ".jsonl":
                records = tp.iter_jsonl_records(path)
                for obj in records:
                    text_val = str(obj.get("text") or "").strip()
                    if not text_val:
                        continue
                    chunks = tp.chunk_text(tp.clean_text(text_val))
                    base_meta = {
                        "file_path": str(path),
                        "file_name": path.name,
                    }
                    # 透传一些常见业务字段
                    for key in [
                        "domain",
                        "type",
                        "law_code",
                        "law_name",
                        "article_no",
                        "title",
                        "case_id",
                        "source",
                    ]:
                        if obj.get(key) is not None:
                            base_meta[key] = obj.get(key)
                    all_chunks.extend(chunks)
                    per_chunk_meta.extend([{**base_meta} for _ in chunks])

            elif ext == ".json":
                records = tp.load_json_array(path)
                if records:
                    for obj in records:
                        text_val = str(obj.get("text") or "").strip()
                        if not text_val:
                            continue
                        chunks = tp.chunk_text(tp.clean_text(text_val))
                        base_meta = {
                            "file_path": str(path),
                            "file_name": path.name,
                        }
                        for key in [
                            "domain",
                            "type",
                            "law_code",
                            "law_name",
                            "article_no",
                            "title",
                            "case_id",
                            "source",
                        ]:
                            if obj.get(key) is not None:
                                base_meta[key] = obj.get(key)
                        all_chunks.extend(chunks)
                        per_chunk_meta.extend([{**base_meta} for _ in chunks])
                else:
                    # 退化为普通文本
                    res = tp.process_plain_document(path)
                    all_chunks = res.get("chunks", [])
                    base_meta = res.get("metadata", {})
                    per_chunk_meta = [{**base_meta} for _ in all_chunks]
            else:
                res = tp.process_plain_document(path)
                all_chunks = res.get("chunks", [])
                base_meta = res.get("metadata", {})
                per_chunk_meta = [{**base_meta} for _ in all_chunks]

            print(
                f"[knowledge.index] document_id={document_id}, ext={ext}, chunks={len(all_chunks)}"
            )

            if not all_chunks:
                # 允许没有内容，但仍然清空已有 chunks
                db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document_id).delete()
                doc.status = "indexed"
                db.commit()
                return jsonify({"document_id": document_id, "chunk_count": 0, "status": doc.status})

            print(f"generate_embeddings_batch start")
            embeddings = generate_embeddings_batch(all_chunks)
            print(f"generate_embeddings_batch end")
            # 对齐长度
            if len(embeddings) != len(all_chunks):
                n = min(len(embeddings), len(all_chunks))
                all_chunks = all_chunks[:n]
                embeddings = embeddings[:n]
                per_chunk_meta = per_chunk_meta[:n]

            # 统计旧的 chunks 数量
            old_count = (
                db.query(KnowledgeChunk)
                .filter(KnowledgeChunk.document_id == document_id)
                .count()
            )
            print(
                f"[knowledge.index] document_id={document_id}, old_chunks={old_count}, will_insert={len(all_chunks)}"
            )

            # 清理旧数据
            deleted = (
                db.query(KnowledgeChunk)
                .filter(KnowledgeChunk.document_id == document_id)
                .delete(synchronize_session=False)
            )
            print(
                f"[knowledge.index] document_id={document_id}, deleted_old_chunks={deleted}"
            )

            # 写入新 chunks
            for idx, (text, emb, meta) in enumerate(zip(all_chunks, embeddings, per_chunk_meta)):
                ch = KnowledgeChunk(
                    document_id=document_id,
                    chunk_index=idx,
                    section_label=meta.get("article_no") or meta.get("title"),
                    text=text,
                    tags=None,
                    embedding=emb,
                    importance=0.5,
                    extra_metadata=meta,
                )
                db.add(ch)

            doc.status = "indexed"
            db.commit()

            db_count = (
                db.query(KnowledgeChunk)
                .filter(KnowledgeChunk.document_id == document_id)
                .count()
            )
            print(
                f"[knowledge.index] success document_id={document_id}, chunks={len(all_chunks)}, db_count={db_count}"
            )

            return jsonify(
                {
                    "document_id": document_id,
                    "chunk_count": len(all_chunks),
                    "status": doc.status,
                }
            )
        except Exception as e:  # noqa: BLE001
            doc.status = "error"
            db.commit()
            print(f"[knowledge.index] error document_id={document_id}: {e}")
            return (
                jsonify({"error": "index failed", "detail": str(e)}),
                500,
            )
    finally:
        db.close()


@knowledge_bp.post("/documents")
@flask_auth_required(scopes=[Scopes.WRITE_KNOWLEDGE])
def create_document():
    payload = request.get_json(force=True) or {}

    collection_id = payload.get("collection_id")
    title = (payload.get("title") or "").strip()
    if not collection_id or not title:
        return jsonify({"error": "fields 'collection_id' and 'title' are required"}), 400

    external_id = payload.get("external_id")
    source_uri = payload.get("source_uri")
    metadata = payload.get("metadata")

    db: Session = SessionLocal()
    try:
        # 租户隔离：验证用户有权访问该 collection
        q = db.query(KnowledgeCollection).filter(KnowledgeCollection.id == int(collection_id))
        q = apply_project_filter(q, KnowledgeCollection)
        if not q.first():
            return jsonify({"error": "collection not found or access denied"}), 404
        
        doc = KnowledgeDocument(
            collection_id=int(collection_id),
            external_id=external_id,
            title=title,
            source_uri=source_uri,
            extra_metadata=metadata,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        return (
            jsonify(
                {
                    "id": doc.id,
                    "collection_id": doc.collection_id,
                    "external_id": doc.external_id,
                    "title": doc.title,
                    "source_uri": doc.source_uri,
                    "metadata": doc.extra_metadata,
                    "status": doc.status,
                    "created_at": to_beijing_iso(doc.created_at),
                    "updated_at": to_beijing_iso(doc.updated_at),
                }
            ),
            201,
        )
    finally:
        db.close()


@knowledge_bp.get("/documents")
@flask_auth_required(scopes=[Scopes.READ_KNOWLEDGE])
def list_documents():
    collection_id = request.args.get("collection_id")
    status = request.args.get("status")

    db: Session = SessionLocal()
    try:
        # 关联 collection 以实现租户隔离
        q = db.query(KnowledgeDocument).join(
            KnowledgeCollection, KnowledgeDocument.collection_id == KnowledgeCollection.id
        )
        
        # 应用租户隔离
        q = apply_project_filter(q, KnowledgeCollection)
        
        if collection_id:
            q = q.filter(KnowledgeDocument.collection_id == int(collection_id))
        if status:
            q = q.filter(KnowledgeDocument.status == status)

        items = []
        for doc in q.order_by(KnowledgeDocument.created_at.desc()).all():
            items.append(
                {
                    "id": doc.id,
                    "collection_id": doc.collection_id,
                    "external_id": doc.external_id,
                    "title": doc.title,
                    "source_uri": doc.source_uri,
                    "metadata": doc.extra_metadata,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat(),
                    "updated_at": doc.updated_at.isoformat(),
                }
            )

        return jsonify({"items": items})
    finally:
        db.close()


@knowledge_bp.get("/documents/<int:document_id>/chunks")
@flask_auth_required(scopes=[Scopes.READ_KNOWLEDGE])
def list_chunks(document_id: int):
    db: Session = SessionLocal()
    try:
        # 先验证对文档的访问权限（租户隔离）
        doc_q = db.query(KnowledgeDocument).join(
            KnowledgeCollection, KnowledgeDocument.collection_id == KnowledgeCollection.id
        ).filter(KnowledgeDocument.id == document_id)
        doc_q = apply_project_filter(doc_q, KnowledgeCollection)
        if not doc_q.first():
            return jsonify({"error": "document not found or access denied"}), 404
        
        q = (
            db.query(KnowledgeChunk)
            .filter(KnowledgeChunk.document_id == document_id)
            .order_by(KnowledgeChunk.chunk_index.asc())
        )

        items = []
        for ch in q.all():
            items.append(
                {
                    "id": ch.id,
                    "document_id": ch.document_id,
                    "chunk_index": ch.chunk_index,
                    "section_label": ch.section_label,
                    "text": ch.text,
                    "tags": ch.tags,
                    "importance": ch.importance,
                    "metadata": ch.extra_metadata,
                }
            )

        return jsonify({"items": items})
    finally:
        db.close()


@knowledge_bp.post("/chunks/ingest")
@flask_auth_required(scopes=[Scopes.WRITE_KNOWLEDGE])
def ingest_chunk():
    """直接写入单个知识块（用于知识沉淀）
    
    请求体:
    {
        "collection_id": 1,          // 目标集合 ID（可选，如无则自动创建）
        "domain": "test_experience", // 领域
        "text": "知识内容...",
        "tags": ["tag1", "tag2"],
        "embedding": [0.1, 0.2, ...],  // 可选，已预计算的向量
        "importance": 0.8,
        "metadata": {...}
    }
    """
    from processing.embedding_processing import generate_embeddings_batch
    
    payload = request.get_json(force=True) or {}
    
    collection_id = payload.get("collection_id")
    domain = payload.get("domain", "experience")
    text = (payload.get("text") or "").strip()
    tags = payload.get("tags")
    embedding = payload.get("embedding")
    importance = float(payload.get("importance", 0.5))
    metadata = payload.get("metadata") or {}
    
    if not text:
        return jsonify({"error": "field 'text' is required"}), 400
    
    # 获取租户上下文中的 project_id
    ctx = getattr(g, "tenant_ctx", {}) or {}
    ctx_project_id = ctx.get("project_id")
    
    db: Session = SessionLocal()
    try:
        # 1. 获取或创建集合
        if collection_id:
            q = db.query(KnowledgeCollection).filter(KnowledgeCollection.id == collection_id)
            q = apply_project_filter(q, KnowledgeCollection)
            col = q.first()
            if not col:
                return jsonify({"error": f"collection {collection_id} not found or access denied"}), 404
        else:
            # 按 domain + project_id 查找或创建
            q = db.query(KnowledgeCollection).filter(KnowledgeCollection.domain == domain)
            q = apply_project_filter(q, KnowledgeCollection)
            col = q.first()
            if not col:
                col = KnowledgeCollection(
                    name=f"{domain}_auto",
                    domain=domain,
                    project_id=ctx_project_id,  # 绑定到当前租户
                    description=f"Auto-created collection for {domain}",
                )
                db.add(col)
                db.flush()
        
        # 2. 创建虚拟文档（用于组织 chunks）
        doc_title = metadata.get("source", "insight") + f"_{col.id}"
        doc = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.collection_id == col.id,
            KnowledgeDocument.title == doc_title,
        ).first()
        
        if not doc:
            doc = KnowledgeDocument(
                collection_id=col.id,
                title=doc_title,
                source_uri="knowledge_insight",
                status="indexed",
            )
            db.add(doc)
            db.flush()
        
        # 3. 生成 embedding（如果没有传入）
        if not embedding:
            try:
                emb_list = generate_embeddings_batch([text])
                embedding = emb_list[0] if emb_list else None
            except Exception:
                pass
        
        # 4. 获取 chunk_index
        max_idx = db.query(KnowledgeChunk.chunk_index).filter(
            KnowledgeChunk.document_id == doc.id
        ).order_by(KnowledgeChunk.chunk_index.desc()).first()
        chunk_index = (max_idx[0] + 1) if max_idx else 0
        
        # 5. 创建 chunk
        chunk = KnowledgeChunk(
            document_id=doc.id,
            chunk_index=chunk_index,
            section_label=metadata.get("category"),
            text=text,
            tags=tags,
            embedding=embedding,
            importance=importance,
            extra_metadata=metadata,
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        
        return jsonify({
            "success": True,
            "chunk_id": chunk.id,
            "collection_id": col.id,
            "document_id": doc.id,
        }), 201
        
    finally:
        db.close()
