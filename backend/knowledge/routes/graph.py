from __future__ import annotations

import sys
import hashlib
from pathlib import Path

from flask import Blueprint, jsonify, request, Response, g
from loguru import logger

# 添加 shared 模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.auth import flask_auth_required, Scopes
from ..tools.graph_client import get_neo4j_driver


graph_bp = Blueprint("graph", __name__)


# 注意：图谱数据目前是全局共享的，不按 project_id 隔离
# 如需隔离，需要在 Neo4j 节点中添加 project_id 属性


def _get_cache_service():
    """获取缓存服务（失败返回 None）"""
    try:
        from shared.cache import get_cache_service
        return get_cache_service()
    except Exception:
        return None


def _graph_query_hash(query: str) -> str:
    """生成图谱查询哈希"""
    return hashlib.md5(query.encode()).hexdigest()[:16]


def _node_to_dict(val):
    """Serialize Neo4j Node (or dict/primitive) into a JSON-safe dict.

    This mirrors the behavior from embeddingETL's /graph/query implementation
    so that existing frontends expecting fields like identity/labels/properties
    continue to work.
    """

    # Neo4j Node: has labels/id/items
    if hasattr(val, "labels") and hasattr(val, "id") and hasattr(val, "items"):
        node_id = getattr(val, "id", None) or getattr(val, "element_id", None)
        # 清洗属性：将非基础类型转成字符串，避免 JSON 序列化错误
        raw_props = dict(val.items())
        props: dict[str, object] = {}
        for k, v in raw_props.items():
            if isinstance(v, (dict, list, str, int, float, bool)) or v is None:
                props[k] = v
            else:
                props[k] = str(v)

        return {
            "identity": node_id,
            "labels": list(val.labels),
            "properties": props,
        }

    # Already a plain dict
    if isinstance(val, dict):
        return {
            "identity": None,
            "labels": [],
            "properties": val,
        }

    # Fallback: stringify
    return {
        "identity": None,
        "labels": [],
        "properties": {"value": str(val)},
    }


def _sanitize_any(obj):
    """Recursively sanitize any Python object into a JSON-serializable form.

    - Primitives / None: 原样返回
    - dict / list: 递归处理其内部元素
    - Neo4j Node / Relationship: 复用现有逻辑再递归
    - 其它对象：转成 str
    """

    # primitives
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj

    # dict
    if isinstance(obj, dict):
        return {k: _sanitize_any(v) for k, v in obj.items()}

    # list / tuple
    if isinstance(obj, (list, tuple)):
        return [_sanitize_any(v) for v in obj]

    # Node-like
    if hasattr(obj, "labels") and hasattr(obj, "id") and hasattr(obj, "items"):
        return _sanitize_any(_node_to_dict(obj))

    # Relationship-like
    if hasattr(obj, "type") and hasattr(obj, "start_node"):
        raw_rel_props = dict(obj.items()) if hasattr(obj, "items") else {}
        rel_props = {rk: _sanitize_any(rv) for rk, rv in raw_rel_props.items()}
        return {
            "identity": getattr(obj, "id", None) or getattr(obj, "element_id", None),
            "type": obj.type,
            "start": getattr(getattr(obj, "start_node", None), "id", None),
            "end": getattr(getattr(obj, "end_node", None), "id", None),
            "properties": rel_props,
        }

    # fallback
    return str(obj)


@graph_bp.route("/query", methods=["POST"])
def query_graph():
    data = request.get_json(silent=True) or {}
    cypher = (data.get("cypher") or "").strip()

    if not cypher:
        return jsonify({"error": "cypher is required"}), 400

    try:
        driver = get_neo4j_driver()
        records = []
        max_records = 1000

        # 简单打印收到的 Cypher，便于调试
        logger.debug(f"[Graph] Query cypher: {cypher}")

        with driver.session() as session:
            # Add a defensive LIMIT if user forgot one
            text = cypher
            if "limit" not in text.lower():
                text += " LIMIT 100"

            result = session.run(text, timeout=30)

            count = 0
            for record in result:
                if count >= max_records:
                    break

                item = {}
                for key in record.keys():
                    val = record[key]

                    # 列表形式的关系（例如 r*1..1 返回的路径），转换为关系字典数组
                    if isinstance(val, list) and val and hasattr(val[0], "type") and hasattr(val[0], "start_node"):
                        rel_list = []
                        for rel in val:
                            raw_rel_props = dict(rel.items()) if hasattr(rel, "items") else {}
                            rel_props: dict[str, object] = {}
                            for rk, rv in raw_rel_props.items():
                                if isinstance(rv, (dict, list, str, int, float, bool)) or rv is None:
                                    rel_props[rk] = rv
                                else:
                                    rel_props[rk] = str(rv)

                            rel_list.append(
                                {
                                    "identity": getattr(rel, "id", None) or getattr(rel, "element_id", None),
                                    "type": rel.type,
                                    "start": getattr(getattr(rel, "start_node", None), "id", None),
                                    "end": getattr(getattr(rel, "end_node", None), "id", None),
                                    "properties": rel_props,
                                }
                            )

                        item[key] = rel_list
                    # 任何具有 Node 特征的对象统一序列化为节点
                    elif hasattr(val, "labels") and hasattr(val, "id") and hasattr(val, "items"):
                        item[key] = _node_to_dict(val)
                    # Relationship: has type & start_node
                    elif hasattr(val, "type") and hasattr(val, "start_node"):
                        # 关系属性同样需要清洗，避免非 JSON 类型导致序列化失败
                        raw_rel_props = dict(val.items()) if hasattr(val, "items") else {}
                        rel_props: dict[str, object] = {}
                        for rk, rv in raw_rel_props.items():
                            if isinstance(rv, (dict, list, str, int, float, bool)) or rv is None:
                                rel_props[rk] = rv
                            else:
                                rel_props[rk] = str(rv)

                        item[key] = {
                            "identity": getattr(val, "id", None) or getattr(val, "element_id", None),
                            "type": val.type,
                            "start": getattr(getattr(val, "start_node", None), "id", None),
                            "end": getattr(getattr(val, "end_node", None), "id", None),
                            "properties": rel_props,
                        }
                    # 简单可 JSON 化类型（dict / list / str / int / float / bool / None）原样返回
                    elif isinstance(val, (dict, list, str, int, float, bool)) or val is None:
                        item[key] = val
                    # 其它复杂对象统一转成字符串，避免 not JSON serializable 错误
                    else:
                        item[key] = str(val)

                records.append(item)
                count += 1

        logger.debug(f"[Graph] Query returned {len(records)} records")

        # 为了彻底规避 JSON 序列化问题，这里直接使用 json.dumps + default=str
        import json

        payload = {"result": records}
        text = json.dumps(payload, ensure_ascii=False, default=str)
        return Response(text, mimetype="application/json")
    except Exception as e:
        logger.exception(f"[Graph] Query error: {e}")
        return jsonify({"error": f"Query failed: {e}"}), 500


@graph_bp.route("/reset", methods=["POST"])
def reset_graph():
  """清空整个图谱：删除所有节点和关系。

  警告：这是高危操作，只适用于开发 / 测试环境或明确需要整体重建图谱的场景。
  """

  try:
    driver = get_neo4j_driver()
    with driver.session() as session:
      session.run("MATCH (n) DETACH DELETE n")
      # 再检查一遍剩余节点数
      res = session.run("MATCH (n) RETURN count(n) AS cnt")
      cnt = res.single()["cnt"]

    status = "success" if cnt == 0 else "partial"
    return jsonify({"status": status, "remaining_nodes": int(cnt)})
  except Exception as e:
    logger.exception(f"[Graph] Reset error: {e}")
    return jsonify({"error": f"Reset failed: {e}"}), 500


@graph_bp.route("/delete_node", methods=["POST"])
def delete_node():
  """根据节点 identity 删除单个节点及其关系。

  请求体示例： {"identity": "4:...:0"} 或 {"identity": 123}
  会同时尝试通过 id(n) 与 elementId(n) 匹配。
  """

  data = request.get_json(silent=True) or {}
  identity = data.get("identity")
  if identity is None:
    return jsonify({"error": "identity is required"}), 400

  id_str = str(identity)
  try:
    id_int = int(identity)
  except Exception:  # noqa: BLE001
    id_int = -1  # 不会匹配任何 id(n)

  try:
    driver = get_neo4j_driver()
    with driver.session() as session:
      res = session.run(
        "MATCH (n) WHERE id(n) = $id_int OR elementId(n) = $id_str "
        "WITH n, count(n) AS c MATCH (n) DETACH DELETE n RETURN c AS deleted",
        id_int=id_int,
        id_str=id_str,
      )
      rec = res.single()
      deleted = int(rec["deleted"] if rec and "deleted" in rec else 0)

    return jsonify({"identity": identity, "deleted": deleted})
  except Exception as e:
    logger.exception(f"[Graph] Delete node error: {e}")
    return jsonify({"error": f"Delete node failed: {e}"}), 500


@graph_bp.route("/delete_relation", methods=["POST"])
def delete_relation():
  """根据关系 identity 删除单条关系。

  请求体示例： {"identity": "5:...:0"} 或 {"identity": 456}
  同时尝试通过 id(r) 与 elementId(r) 匹配。
  """

  data = request.get_json(silent=True) or {}
  identity = data.get("identity")
  if identity is None:
    return jsonify({"error": "identity is required"}), 400

  id_str = str(identity)
  try:
    id_int = int(identity)
  except Exception:  # noqa: BLE001
    id_int = -1

  try:
    driver = get_neo4j_driver()
    with driver.session() as session:
      res = session.run(
        "MATCH ()-[r]->() WHERE id(r) = $id_int OR elementId(r) = $id_str "
        "DELETE r RETURN count(r) AS deleted",
        id_int=id_int,
        id_str=id_str,
      )
      rec = res.single()
      deleted = int(rec["deleted"] if rec and "deleted" in rec else 0)

    return jsonify({"identity": identity, "deleted": deleted})
  except Exception as e:
    logger.exception(f"[Graph] Delete relation error: {e}")
    return jsonify({"error": f"Delete relation failed: {e}"}), 500


# ============================================================
# 知识图谱增强 API
# ============================================================

@graph_bp.route("/extract", methods=["POST"])
@flask_auth_required(scopes=[Scopes.WRITE_KNOWLEDGE])
def extract_entities():
    """从文本中抽取实体和关系，并写入图谱
    
    请求体：
    {
        "text": "要分析的文本",
        "domain": "law",  // 可选，领域标识
        "source_id": "chunk_123"  // 可选，来源标识
    }
    """
    from services.graph_service import get_graph_service
    
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    
    if not text:
        return jsonify({"error": "text is required"}), 400
    
    domain = data.get("domain")
    source_id = data.get("source_id")
    
    # 获取租户上下文中的 project_id
    ctx = getattr(g, "tenant_ctx", {}) or {}
    project_id = ctx.get("project_id") or data.get("project_id")
    
    try:
        service = get_graph_service()
        result = service.build_graph_from_text(text, domain, source_id, project_id)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"[Graph] Extract error: {e}")
        return jsonify({"error": str(e)}), 500


@graph_bp.route("/search", methods=["POST"])
@flask_auth_required(scopes=[Scopes.READ_KNOWLEDGE])
def search_graph():
    """搜索图谱实体（带缓存）"""
    from services.graph_service import get_graph_service
    
    data = request.get_json(silent=True) or {}
    keyword = (data.get("keyword") or "").strip()
    
    if not keyword:
        return jsonify({"error": "keyword is required"}), 400
    
    entity_type = data.get("entity_type")
    limit = int(data.get("limit", 20))
    
    # 获取租户上下文中的 project_id
    ctx = getattr(g, "tenant_ctx", {}) or {}
    project_id = ctx.get("project_id") or data.get("project_id")
    
    # 尝试从缓存获取（缓存 key 包含 project_id）
    cache = _get_cache_service()
    cache_key = _graph_query_hash(f"search:{keyword}:{entity_type or ''}:{limit}:{project_id or ''}")
    if cache:
        cached = cache.get_graph(cache_key)
        if cached:
            logger.debug(f"[Graph] Cache hit for search: {keyword}")
            return jsonify(cached)
    
    try:
        service = get_graph_service()
        entities = service.search_entities(keyword, entity_type, limit, project_id)
        result = {"entities": entities, "count": len(entities)}
        
        # 写入缓存
        if cache:
            cache.set_graph(cache_key, result)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"[Graph] Search error: {e}")
        return jsonify({"error": str(e)}), 500


@graph_bp.route("/neighbors", methods=["POST"])
@flask_auth_required(scopes=[Scopes.READ_KNOWLEDGE])
def get_neighbors():
    """获取实体的邻居节点和关系（带缓存）"""
    from services.graph_service import get_graph_service
    
    data = request.get_json(silent=True) or {}
    entity_name = (data.get("entity_name") or "").strip()
    
    if not entity_name:
        return jsonify({"error": "entity_name is required"}), 400
    
    depth = int(data.get("depth", 1))
    limit = int(data.get("limit", 50))
    
    # 获取租户上下文中的 project_id
    ctx = getattr(g, "tenant_ctx", {}) or {}
    project_id = ctx.get("project_id") or data.get("project_id")
    
    # 尝试从缓存获取（缓存 key 包含 project_id）
    cache = _get_cache_service()
    cache_key = _graph_query_hash(f"neighbors:{entity_name}:{depth}:{limit}:{project_id or ''}")
    if cache:
        cached = cache.get_graph(cache_key)
        if cached:
            logger.debug(f"[Graph] Cache hit for neighbors: {entity_name}")
            return jsonify(cached)
    
    try:
        service = get_graph_service()
        result = service.get_entity_neighbors(entity_name, depth, limit, project_id)
        response = {
            "entities": result.entities,
            "relations": result.relations,
        }
        
        # 写入缓存
        if cache:
            cache.set_graph(cache_key, response)
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"[Graph] Neighbors error: {e}")
        return jsonify({"error": str(e)}), 500


@graph_bp.route("/path", methods=["POST"])
@flask_auth_required(scopes=[Scopes.READ_KNOWLEDGE])
def find_path():
    """查找两个实体之间的路径
    
    请求体：
    {
        "source": "源实体名",
        "target": "目标实体名",
        "max_depth": 4
    }
    """
    from services.graph_service import get_graph_service
    
    data = request.get_json(silent=True) or {}
    source = (data.get("source") or "").strip()
    target = (data.get("target") or "").strip()
    
    if not source or not target:
        return jsonify({"error": "source and target are required"}), 400
    
    max_depth = int(data.get("max_depth", 4))
    
    # 获取租户上下文中的 project_id
    ctx = getattr(g, "tenant_ctx", {}) or {}
    project_id = ctx.get("project_id") or data.get("project_id")
    
    try:
        service = get_graph_service()
        paths = service.find_path(source, target, max_depth, project_id)
        return jsonify({"paths": paths, "count": len(paths)})
    except Exception as e:
        logger.exception(f"[Graph] Path error: {e}")
        return jsonify({"error": str(e)}), 500


@graph_bp.route("/enhanced_search", methods=["POST"])
@flask_auth_required(scopes=[Scopes.READ_KNOWLEDGE])
def enhanced_search():
    """图谱增强的语义搜索
    
    结合实体抽取和图谱遍历，返回结构化的上下文
    
    请求体：
    {
        "query": "查询文本",
        "domain": "law",  // 可选
        "top_k": 10
    }
    """
    from services.graph_service import get_graph_service
    
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    
    if not query:
        return jsonify({"error": "query is required"}), 400
    
    domain = data.get("domain")
    top_k = int(data.get("top_k", 10))
    
    # 获取租户上下文中的 project_id
    ctx = getattr(g, "tenant_ctx", {}) or {}
    project_id = ctx.get("project_id") or data.get("project_id")
    
    try:
        service = get_graph_service()
        result = service.graph_enhanced_search(query, domain, top_k, project_id)
        return jsonify(result)
    except Exception as e:
        import traceback
        print("[graph.enhanced_search] ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@graph_bp.route("/stats", methods=["GET"])
@flask_auth_required(scopes=[Scopes.READ_KNOWLEDGE])
def get_stats():
    """获取图谱统计信息"""
    from services.graph_service import get_graph_service
    
    try:
        service = get_graph_service()
        stats = service.get_stats()
        return jsonify(stats)
    except Exception as e:
        import traceback
        print("[graph.stats] ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@graph_bp.route("/create_entity", methods=["POST"])
@flask_auth_required(scopes=[Scopes.WRITE_KNOWLEDGE])
def create_entity():
    """手动创建实体
    
    请求体：
    {
        "name": "实体名称",
        "type": "Concept",
        "domain": "law",
        "properties": {}
    }
    """
    from services.graph_service import get_graph_service, Entity
    
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    entity_type = data.get("type", "Concept")
    
    if not name:
        return jsonify({"error": "name is required"}), 400
    
    domain = data.get("domain")
    properties = data.get("properties", {})
    
    # 获取租户上下文中的 project_id
    ctx = getattr(g, "tenant_ctx", {}) or {}
    project_id = ctx.get("project_id") or data.get("project_id")
    
    try:
        service = get_graph_service()
        entity = Entity(name=name, type=entity_type, properties=properties)
        node_id = service.create_entity(entity, domain, project_id)
        
        if node_id is not None:
            return jsonify({"success": True, "node_id": node_id, "project_id": project_id})
        else:
            return jsonify({"success": False, "error": "Failed to create entity"}), 500
    except Exception as e:
        import traceback
        print("[graph.create_entity] ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@graph_bp.route("/create_relation", methods=["POST"])
@flask_auth_required(scopes=[Scopes.WRITE_KNOWLEDGE])
def create_relation():
    """手动创建关系
    
    请求体：
    {
        "source": "源实体名",
        "target": "目标实体名",
        "type": "RELATED_TO",
        "properties": {}
    }
    """
    from services.graph_service import get_graph_service, Relation
    
    data = request.get_json(silent=True) or {}
    source = (data.get("source") or "").strip()
    target = (data.get("target") or "").strip()
    rel_type = data.get("type", "RELATED_TO")
    
    if not source or not target:
        return jsonify({"error": "source and target are required"}), 400
    
    properties = data.get("properties", {})
    
    # 获取租户上下文中的 project_id
    ctx = getattr(g, "tenant_ctx", {}) or {}
    project_id = ctx.get("project_id") or data.get("project_id")
    
    try:
        service = get_graph_service()
        relation = Relation(source=source, target=target, type=rel_type, properties=properties)
        success = service.create_relation(relation, project_id)
        
        return jsonify({"success": success})
    except Exception as e:
        import traceback
        print("[graph.create_relation] ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
