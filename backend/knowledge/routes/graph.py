from __future__ import annotations

from flask import Blueprint, jsonify, request, Response

from tools.graph_client import get_neo4j_driver


graph_bp = Blueprint("graph", __name__)


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
        print(f"[graph.query] incoming cypher: {cypher}")

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

        print(f"[graph.query] records returned: {len(records)}")
        # 打印前几条记录结构，便于调试
        print("[graph.query] sample records:", records[:2])

        # 为了彻底规避 JSON 序列化问题，这里直接使用 json.dumps + default=str
        import json

        payload = {"result": records}
        text = json.dumps(payload, ensure_ascii=False, default=str)
        return Response(text, mimetype="application/json")
    except Exception as e:  # pragma: no cover - simple error wrapper
        # 将完整异常打到控制台，方便排查
        import traceback

        print("[graph.query] ERROR:", e)
        traceback.print_exc()
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
  except Exception as e:  # pragma: no cover
    import traceback

    print("[graph.reset] ERROR:", e)
    traceback.print_exc()
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
  except Exception as e:  # pragma: no cover
    import traceback

    print("[graph.delete_node] ERROR:", e)
    traceback.print_exc()
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
  except Exception as e:  # pragma: no cover
    import traceback

    print("[graph.delete_relation] ERROR:", e)
    traceback.print_exc()
    return jsonify({"error": f"Delete relation failed: {e}"}), 500
