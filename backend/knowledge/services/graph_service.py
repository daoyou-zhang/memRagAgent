"""知识图谱服务

提供实体抽取、关系构建、图谱查询等功能。
结合 LLM 和 Neo4j 实现知识图谱的自动构建与检索。
"""
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from tools.graph_client import get_neo4j_driver


@dataclass
class Entity:
    """实体"""
    name: str
    type: str  # Person, Concept, Event, Location, Organization, etc.
    properties: Dict[str, Any] = field(default_factory=dict)
    

@dataclass  
class Relation:
    """关系"""
    source: str  # 源实体名
    target: str  # 目标实体名
    type: str    # 关系类型
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphSearchResult:
    """图谱搜索结果"""
    entities: List[Dict]
    relations: List[Dict]
    paths: List[Dict]
    

class KnowledgeGraphService:
    """知识图谱服务"""
    
    # 实体类型定义
    ENTITY_TYPES = [
        "Person",       # 人物
        "Concept",      # 概念
        "Event",        # 事件
        "Location",     # 地点
        "Organization", # 组织
        "Time",         # 时间
        "Product",      # 产品
        "Law",          # 法律条款
        "Term",         # 术语
    ]
    
    # 关系类型定义
    RELATION_TYPES = [
        "RELATED_TO",      # 相关
        "BELONGS_TO",      # 属于
        "CAUSES",          # 导致
        "CONTAINS",        # 包含
        "FOLLOWS",         # 跟随/继承
        "DEFINES",         # 定义
        "REFERENCES",      # 引用
        "CONFLICTS_WITH",  # 冲突
        "SUPPORTS",        # 支持
        "DEPENDS_ON",      # 依赖
    ]
    
    def __init__(self):
        self.driver = get_neo4j_driver()
    
    # ========== 实体抽取 ==========
    
    def extract_entities_from_text(self, text: str, domain: str = None) -> List[Entity]:
        """使用 LLM 从文本中抽取实体
        
        Args:
            text: 输入文本
            domain: 领域（可选，用于优化抽取）
        
        Returns:
            Entity 列表
        """
        from processing.llm_processing import call_llm
        
        prompt = f"""请从以下文本中抽取关键实体。

文本：
{text}

请以 JSON 格式返回实体列表，每个实体包含：
- name: 实体名称
- type: 实体类型（可选值：{', '.join(self.ENTITY_TYPES)}）
- properties: 属性字典（可选）

示例输出：
[
  {{"name": "劳动合同法", "type": "Law", "properties": {{"code": "劳动合同法"}}}},
  {{"name": "经济补偿", "type": "Concept", "properties": {{}}}}
]

只返回 JSON 数组，不要其他内容。"""

        try:
            response = call_llm(prompt, max_tokens=2000)
            # 解析 JSON
            entities_data = json.loads(response.strip())
            entities = []
            for e in entities_data:
                entities.append(Entity(
                    name=e.get("name", ""),
                    type=e.get("type", "Concept"),
                    properties=e.get("properties", {}),
                ))
            return entities
        except Exception as e:
            print(f"[GraphService] extract_entities error: {e}")
            return []
    
    def extract_relations_from_text(
        self, 
        text: str, 
        entities: List[Entity],
        domain: str = None,
    ) -> List[Relation]:
        """使用 LLM 从文本中抽取实体间的关系
        
        Args:
            text: 输入文本
            entities: 已抽取的实体列表
            domain: 领域
        
        Returns:
            Relation 列表
        """
        from processing.llm_processing import call_llm
        
        entity_names = [e.name for e in entities]
        
        prompt = f"""请从以下文本中抽取实体之间的关系。

文本：
{text}

已识别的实体：
{', '.join(entity_names)}

请以 JSON 格式返回关系列表，每个关系包含：
- source: 源实体名
- target: 目标实体名  
- type: 关系类型（可选值：{', '.join(self.RELATION_TYPES)}）
- properties: 属性字典（可选）

示例输出：
[
  {{"source": "劳动者", "target": "经济补偿", "type": "RELATED_TO", "properties": {{"description": "有权获得"}}}},
  {{"source": "经济补偿", "target": "劳动合同法", "type": "BELONGS_TO", "properties": {{}}}}
]

只返回 JSON 数组，不要其他内容。"""

        try:
            response = call_llm(prompt, max_tokens=2000)
            relations_data = json.loads(response.strip())
            relations = []
            for r in relations_data:
                # 验证源和目标实体存在
                if r.get("source") in entity_names and r.get("target") in entity_names:
                    relations.append(Relation(
                        source=r.get("source", ""),
                        target=r.get("target", ""),
                        type=r.get("type", "RELATED_TO"),
                        properties=r.get("properties", {}),
                    ))
            return relations
        except Exception as e:
            print(f"[GraphService] extract_relations error: {e}")
            return []
    
    # ========== 图谱操作 ==========
    
    def create_entity(self, entity: Entity, domain: str = None) -> Optional[int]:
        """创建实体节点
        
        Returns:
            节点 ID，失败返回 None
        """
        with self.driver.session() as session:
            # 使用 MERGE 避免重复
            cypher = f"""
            MERGE (n:{entity.type} {{name: $name}})
            ON CREATE SET n.created_at = datetime(), n.domain = $domain
            ON MATCH SET n.updated_at = datetime()
            SET n += $properties
            RETURN id(n) as node_id
            """
            result = session.run(
                cypher,
                name=entity.name,
                domain=domain or "",
                properties=entity.properties,
            )
            record = result.single()
            return record["node_id"] if record else None
    
    def create_relation(self, relation: Relation) -> bool:
        """创建关系
        
        Returns:
            是否成功
        """
        with self.driver.session() as session:
            # 动态匹配源和目标节点（不限制类型）
            cypher = f"""
            MATCH (a {{name: $source}})
            MATCH (b {{name: $target}})
            MERGE (a)-[r:{relation.type}]->(b)
            ON CREATE SET r.created_at = datetime()
            SET r += $properties
            RETURN id(r) as rel_id
            """
            result = session.run(
                cypher,
                source=relation.source,
                target=relation.target,
                properties=relation.properties,
            )
            record = result.single()
            return record is not None
    
    def build_graph_from_text(
        self, 
        text: str, 
        domain: str = None,
        source_id: str = None,
    ) -> Dict[str, Any]:
        """从文本构建知识图谱
        
        完整流程：文本 → 实体抽取 → 关系抽取 → 写入 Neo4j
        
        Args:
            text: 输入文本
            domain: 领域标识
            source_id: 来源标识（如 chunk_id）
        
        Returns:
            构建结果统计
        """
        # 1. 抽取实体
        entities = self.extract_entities_from_text(text, domain)
        
        # 2. 抽取关系
        relations = []
        if len(entities) >= 2:
            relations = self.extract_relations_from_text(text, entities, domain)
        
        # 3. 写入图谱
        created_entities = 0
        created_relations = 0
        
        for entity in entities:
            if source_id:
                entity.properties["source_id"] = source_id
            node_id = self.create_entity(entity, domain)
            if node_id is not None:
                created_entities += 1
        
        for relation in relations:
            if self.create_relation(relation):
                created_relations += 1
        
        return {
            "extracted_entities": len(entities),
            "extracted_relations": len(relations),
            "created_entities": created_entities,
            "created_relations": created_relations,
            "entities": [{"name": e.name, "type": e.type} for e in entities],
            "relations": [{"source": r.source, "target": r.target, "type": r.type} for r in relations],
        }
    
    # ========== 图谱查询 ==========
    
    def search_entities(
        self, 
        keyword: str, 
        entity_type: str = None,
        limit: int = 20,
    ) -> List[Dict]:
        """搜索实体
        
        Args:
            keyword: 关键词（模糊匹配 name）
            entity_type: 实体类型过滤
            limit: 返回数量
        
        Returns:
            实体列表
        """
        with self.driver.session() as session:
            if entity_type:
                cypher = f"""
                MATCH (n:{entity_type})
                WHERE n.name CONTAINS $keyword
                RETURN n, labels(n) as labels, id(n) as node_id
                LIMIT $limit
                """
            else:
                cypher = """
                MATCH (n)
                WHERE n.name CONTAINS $keyword
                RETURN n, labels(n) as labels, id(n) as node_id
                LIMIT $limit
                """
            
            result = session.run(cypher, keyword=keyword, limit=limit)
            
            entities = []
            for record in result:
                node = record["n"]
                entities.append({
                    "id": record["node_id"],
                    "name": node.get("name"),
                    "type": record["labels"][0] if record["labels"] else "Unknown",
                    "properties": dict(node),
                })
            
            return entities
    
    def get_entity_neighbors(
        self, 
        entity_name: str,
        depth: int = 1,
        limit: int = 50,
    ) -> GraphSearchResult:
        """获取实体的邻居节点和关系
        
        Args:
            entity_name: 实体名称
            depth: 搜索深度
            limit: 返回数量
        
        Returns:
            GraphSearchResult
        """
        with self.driver.session() as session:
            cypher = f"""
            MATCH (center {{name: $name}})
            CALL apoc.path.subgraphAll(center, {{
                maxLevel: $depth,
                limit: $limit
            }})
            YIELD nodes, relationships
            RETURN nodes, relationships
            """
            
            # 简化版（不依赖 APOC）
            cypher = f"""
            MATCH path = (center {{name: $name}})-[r*1..{depth}]-(neighbor)
            WITH center, collect(DISTINCT neighbor) as neighbors, collect(DISTINCT r) as rels
            RETURN center, neighbors, rels
            LIMIT 1
            """
            
            try:
                result = session.run(cypher, name=entity_name, depth=depth, limit=limit)
                record = result.single()
                
                if not record:
                    return GraphSearchResult(entities=[], relations=[], paths=[])
                
                entities = []
                relations = []
                
                # 中心节点
                center = record["center"]
                entities.append({
                    "id": center.id,
                    "name": center.get("name"),
                    "type": list(center.labels)[0] if center.labels else "Unknown",
                    "properties": dict(center),
                    "is_center": True,
                })
                
                # 邻居节点
                for node in record["neighbors"]:
                    entities.append({
                        "id": node.id,
                        "name": node.get("name"),
                        "type": list(node.labels)[0] if node.labels else "Unknown",
                        "properties": dict(node),
                    })
                
                # 关系
                for rel_list in record["rels"]:
                    for rel in rel_list:
                        relations.append({
                            "id": rel.id,
                            "type": rel.type,
                            "source": rel.start_node.id,
                            "target": rel.end_node.id,
                            "properties": dict(rel),
                        })
                
                return GraphSearchResult(
                    entities=entities,
                    relations=relations,
                    paths=[],
                )
                
            except Exception as e:
                print(f"[GraphService] get_entity_neighbors error: {e}")
                return GraphSearchResult(entities=[], relations=[], paths=[])
    
    def find_path(
        self,
        source_name: str,
        target_name: str,
        max_depth: int = 4,
    ) -> List[Dict]:
        """查找两个实体之间的路径
        
        Args:
            source_name: 源实体名
            target_name: 目标实体名
            max_depth: 最大深度
        
        Returns:
            路径列表
        """
        with self.driver.session() as session:
            cypher = f"""
            MATCH path = shortestPath(
                (a {{name: $source}})-[*1..{max_depth}]-(b {{name: $target}})
            )
            RETURN path
            LIMIT 5
            """
            
            result = session.run(cypher, source=source_name, target=target_name)
            
            paths = []
            for record in result:
                path = record["path"]
                path_data = {
                    "nodes": [],
                    "relationships": [],
                }
                
                for node in path.nodes:
                    path_data["nodes"].append({
                        "id": node.id,
                        "name": node.get("name"),
                        "type": list(node.labels)[0] if node.labels else "Unknown",
                    })
                
                for rel in path.relationships:
                    path_data["relationships"].append({
                        "id": rel.id,
                        "type": rel.type,
                        "source": rel.start_node.id,
                        "target": rel.end_node.id,
                    })
                
                paths.append(path_data)
            
            return paths
    
    # ========== 图谱增强 RAG ==========
    
    def graph_enhanced_search(
        self,
        query: str,
        domain: str = None,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """图谱增强的语义搜索
        
        流程：
        1. 从查询中抽取实体
        2. 在图谱中搜索相关实体和关系
        3. 扩展搜索到邻居节点
        4. 返回结构化的图谱上下文
        
        Args:
            query: 查询文本
            domain: 领域过滤
            top_k: 返回数量
        
        Returns:
            图谱上下文
        """
        # 1. 从查询抽取实体
        query_entities = self.extract_entities_from_text(query, domain)
        
        if not query_entities:
            # 无法抽取实体，尝试关键词搜索
            keywords = query.split()[:3]  # 取前3个词
            all_entities = []
            for kw in keywords:
                if len(kw) >= 2:
                    all_entities.extend(self.search_entities(kw, limit=5))
            
            return {
                "query_entities": [],
                "graph_entities": all_entities[:top_k],
                "relations": [],
                "context_text": self._format_graph_context(all_entities, []),
            }
        
        # 2. 搜索图谱中的相关实体
        all_entities = []
        all_relations = []
        
        for entity in query_entities:
            # 精确匹配
            result = self.get_entity_neighbors(entity.name, depth=1, limit=20)
            all_entities.extend(result.entities)
            all_relations.extend(result.relations)
        
        # 去重
        seen_ids = set()
        unique_entities = []
        for e in all_entities:
            if e["id"] not in seen_ids:
                seen_ids.add(e["id"])
                unique_entities.append(e)
        
        seen_rel_ids = set()
        unique_relations = []
        for r in all_relations:
            if r["id"] not in seen_rel_ids:
                seen_rel_ids.add(r["id"])
                unique_relations.append(r)
        
        # 3. 格式化上下文
        context_text = self._format_graph_context(unique_entities, unique_relations)
        
        return {
            "query_entities": [{"name": e.name, "type": e.type} for e in query_entities],
            "graph_entities": unique_entities[:top_k],
            "relations": unique_relations[:top_k * 2],
            "context_text": context_text,
        }
    
    def _format_graph_context(
        self, 
        entities: List[Dict], 
        relations: List[Dict],
    ) -> str:
        """将图谱结果格式化为文本上下文"""
        lines = []
        
        if entities:
            lines.append("【相关实体】")
            for e in entities[:10]:
                type_str = e.get("type", "")
                name = e.get("name", "")
                lines.append(f"  - [{type_str}] {name}")
        
        if relations:
            lines.append("\n【实体关系】")
            # 需要构建 id -> name 映射
            id_to_name = {e["id"]: e.get("name", str(e["id"])) for e in entities}
            
            for r in relations[:10]:
                source_name = id_to_name.get(r.get("source"), str(r.get("source")))
                target_name = id_to_name.get(r.get("target"), str(r.get("target")))
                rel_type = r.get("type", "RELATED_TO")
                lines.append(f"  - {source_name} --[{rel_type}]--> {target_name}")
        
        return "\n".join(lines) if lines else ""
    
    # ========== 统计 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        with self.driver.session() as session:
            # 节点总数
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()["count"]
            
            # 关系总数
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            
            # 按类型统计节点
            result = session.run("""
                MATCH (n) 
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """)
            node_by_type = {r["label"]: r["count"] for r in result}
            
            # 按类型统计关系
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            rel_by_type = {r["type"]: r["count"] for r in result}
            
            return {
                "total_nodes": node_count,
                "total_relations": rel_count,
                "nodes_by_type": node_by_type,
                "relations_by_type": rel_by_type,
            }


# 单例
_graph_service: Optional[KnowledgeGraphService] = None


def get_graph_service() -> KnowledgeGraphService:
    """获取 KnowledgeGraphService 单例"""
    global _graph_service
    if _graph_service is None:
        _graph_service = KnowledgeGraphService()
    return _graph_service
