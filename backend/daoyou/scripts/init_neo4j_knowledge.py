#!/usr/bin/env python3
"""
Neo4j命理知识图谱初始化脚本

这个脚本用于在Neo4j数据库中创建命理知识图谱的基础数据结构。
包括十神、五行、大运、婚姻、事业、财运等节点和关系。

使用方法:
    python scripts/init_neo4j_knowledge.py

环境变量配置:
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=your_password
    NEO4J_DATABASE=neo4j
"""

import os
import sys
from neo4j import GraphDatabase
from typing import Dict, List, Any
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jKnowledgeInitializer:
    """Neo4j知识图谱初始化器"""
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """初始化Neo4j连接"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
    
    def close(self):
        """关闭数据库连接"""
        self.driver.close()
    
    def init_knowledge_graph(self):
        """初始化知识图谱"""

        with self.driver.session(database=self.database) as session:
            # 清空现有数据（可选）
            # session.run("MATCH (n) DETACH DELETE n")
            
            # 创建索引
            self._create_indexes(session)
            
            # 创建十神数据
            self._create_shi_shen_data(session)
            
            # 创建五行数据
            self._create_wu_xing_data(session)
            
            # 创建大运数据
            self._create_da_yun_data(session)
            
            # 创建婚姻数据
            self._create_marriage_data(session)
            
            # 创建事业数据
            self._create_career_data(session)
            
            # 创建财运数据
            self._create_wealth_data(session)
            
            # 创建关系数据
            self._create_relationships(session)
        
    
    def _create_indexes(self, session):
        """创建索引"""

        indexes = [
            "CREATE INDEX shi_shen_name IF NOT EXISTS FOR (s:ShiShen) ON (s.name)",
            "CREATE INDEX wu_xing_element IF NOT EXISTS FOR (w:WuXing) ON (w.element)",
            "CREATE INDEX da_yun_gan_zhi IF NOT EXISTS FOR (d:DaYun) ON (d.gan_zhi)",
            "CREATE INDEX marriage_type IF NOT EXISTS FOR (m:Marriage) ON (m.type)",
            "CREATE INDEX career_type IF NOT EXISTS FOR (c:Career) ON (c.type)",
            "CREATE INDEX wealth_type IF NOT EXISTS FOR (w:Wealth) ON (w.type)"
        ]
        
        for index_query in indexes:
            try:
                session.run(index_query)
            except Exception as e:
                logger.warning(f"创建索引失败: {e}")
    
    def _create_shi_shen_data(self, session):
        """创建十神数据"""
 
        shi_shen_data = [
            {"name": "比肩", "description": "同我者，代表兄弟姐妹、朋友、同事，性格独立，有竞争意识"},
            {"name": "劫财", "description": "同我者，代表竞争对手、小人，性格冲动，容易冲突"},
            {"name": "食神", "description": "我生者，代表子女、学生、下属，性格温和，有才华"},
            {"name": "伤官", "description": "我生者，代表才华、技能、创新，性格叛逆，有创造力"},
            {"name": "偏财", "description": "我克者，代表意外之财、投机，性格慷慨，有冒险精神"},
            {"name": "正财", "description": "我克者，代表正当收入、工资，性格务实，重视物质"},
            {"name": "七杀", "description": "克我者，代表压力、挑战、权威，性格刚强，有领导力"},
            {"name": "正官", "description": "克我者，代表职位、权力、名誉，性格正直，有责任感"},
            {"name": "偏印", "description": "生我者，代表贵人、长辈、学习，性格内向，有智慧"},
            {"name": "正印", "description": "生我者，代表母亲、老师、文化，性格温和，有学识"}
        ]
        
        for data in shi_shen_data:
            query = """
            MERGE (s:ShiShen {name: $name})
            SET s.description = $description
            """
            session.run(query, name=data["name"], description=data["description"])
    
    def _create_wu_xing_data(self, session):
        """创建五行数据"""

        wu_xing_data = [
            {"element": "木", "characteristics": "代表生长、发展、进取，性格正直，有理想"},
            {"element": "火", "characteristics": "代表热情、活力、光明，性格开朗，有领导力"},
            {"element": "土", "characteristics": "代表稳重、踏实、包容，性格温和，有耐心"},
            {"element": "金", "characteristics": "代表坚强、果断、正义，性格刚毅，有原则"},
            {"element": "水", "characteristics": "代表智慧、灵活、适应，性格聪明，有变通"}
        ]
        
        for data in wu_xing_data:
            query = """
            MERGE (w:WuXing {element: $element})
            SET w.characteristics = $characteristics
            """
            session.run(query, element=data["element"], characteristics=data["characteristics"])
    
    def _create_da_yun_data(self, session):
        """创建大运数据"""

        # 这里只是示例数据，实际的大运数据需要根据具体的干支组合
        da_yun_data = [
            {"gan_zhi": "甲子", "meaning": "甲子大运，木水相生，利于学习和发展", "day_master": "甲"},
            {"gan_zhi": "乙丑", "meaning": "乙丑大运，木土相克，需要努力克服困难", "day_master": "乙"},
            {"gan_zhi": "丙寅", "meaning": "丙寅大运，火木相生，利于事业和名声", "day_master": "丙"},
            {"gan_zhi": "丁卯", "meaning": "丁卯大运，火木相生，利于人际关系", "day_master": "丁"},
            {"gan_zhi": "戊辰", "meaning": "戊辰大运，土土相助，稳定发展", "day_master": "戊"}
        ]
        
        for data in da_yun_data:
            query = """
            MERGE (d:DaYun {gan_zhi: $gan_zhi, day_master: $day_master})
            SET d.meaning = $meaning
            """
            session.run(query, **data)
    
    def _create_marriage_data(self, session):
        """创建婚姻数据"""

        marriage_data = [
            {"type": "配偶宫", "meaning": "日支为配偶宫，代表配偶的基本特征"},
            {"type": "配偶星", "meaning": "正财偏财为配偶星，代表配偶的缘分"},
            {"type": "桃花运", "meaning": "桃花运旺的时期，容易遇到心仪对象"},
            {"type": "婚姻时机", "meaning": "适合结婚的时机，需要结合大运流年"}
        ]
        
        for data in marriage_data:
            query = """
            MERGE (m:Marriage {type: $type})
            SET m.meaning = $meaning
            """
            session.run(query, **data)
    
    def _create_career_data(self, session):
        """创建事业数据"""

        career_data = [
            {"type": "官杀星", "meaning": "正官七杀代表事业和权力"},
            {"type": "印绶星", "meaning": "正印偏印代表学习和文化"},
            {"type": "食伤星", "meaning": "食神伤官代表技能和才华"},
            {"type": "财星", "meaning": "正财偏财代表收入和财富"}
        ]
        
        for data in career_data:
            query = """
            MERGE (c:Career {type: $type})
            SET c.meaning = $meaning
            """
            session.run(query, **data)
    
    def _create_wealth_data(self, session):
        """创建财运数据"""

        wealth_data = [
            {"type": "正财", "meaning": "正当收入，工资薪水"},
            {"type": "偏财", "meaning": "意外之财，投资理财"},
            {"type": "财库", "meaning": "财库旺衰影响财运"},
            {"type": "财运时机", "meaning": "财运旺盛的时机"}
        ]
        
        for data in wealth_data:
            query = """
            MERGE (w:Wealth {type: $type})
            SET w.meaning = $meaning
            """
            session.run(query, **data)
    
    def _create_relationships(self, session):
        """创建关系数据"""

        # 创建关系节点
        relationship_data = [
            {"name": "职位", "category": "事业"},
            {"name": "权力", "category": "事业"},
            {"name": "学习", "category": "文化"},
            {"name": "文化", "category": "文化"},
            {"name": "子女", "category": "家庭"},
            {"name": "朋友", "category": "人际关系"},
            {"name": "贵人", "category": "人际关系"},
            {"name": "收入", "category": "财运"},
            {"name": "投资", "category": "财运"},
            {"name": "健康", "category": "健康"},
            {"name": "感情", "category": "婚姻"}
        ]
        
        for data in relationship_data:
            query = """
            MERGE (r:Relationship {name: $name})
            SET r.category = $category
            """
            session.run(query, **data)
        
        # 创建十神与关系的关系
        shi_shen_relationships = [
            ("正官", ["职位", "权力"]),
            ("七杀", ["职位", "权力"]),
            ("正印", ["学习", "文化"]),
            ("偏印", ["学习", "贵人"]),
            ("食神", ["子女", "朋友"]),
            ("伤官", ["才华", "技能"]),
            ("正财", ["收入", "财运"]),
            ("偏财", ["投资", "财运"]),
            ("比肩", ["朋友", "同事"]),
            ("劫财", ["竞争", "冲突"])
        ]
        
        for shi_shen, relationships in shi_shen_relationships:
            for rel in relationships:
                query = """
                MATCH (s:ShiShen {name: $shi_shen})
                MATCH (r:Relationship {name: $relationship})
                MERGE (s)-[:RELATES_TO]->(r)
                """
                session.run(query, shi_shen=shi_shen, relationship=rel)
        
        # 创建五行相生相克关系
        wu_xing_relationships = [
            ("木", "火", "GENERATES"),  # 木生火
            ("火", "土", "GENERATES"),  # 火生土
            ("土", "金", "GENERATES"),  # 土生金
            ("金", "水", "GENERATES"),  # 金生水
            ("水", "木", "GENERATES"),  # 水生木
            ("木", "土", "RESTRAINS"),  # 木克土
            ("土", "水", "RESTRAINS"),  # 土克水
            ("水", "火", "RESTRAINS"),  # 水克火
            ("火", "金", "RESTRAINS"),  # 火克金
            ("金", "木", "RESTRAINS")   # 金克木
        ]
        
        for source, target, rel_type in wu_xing_relationships:
            query = f"""
            MATCH (s:WuXing {{element: $source}})
            MATCH (t:WuXing {{element: $target}})
            MERGE (s)-[:{rel_type}]->(t)
            """
            session.run(query, source=source, target=target)

def main():
    """主函数"""
    # 从环境变量获取配置
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    if not neo4j_password:
        logger.error("请设置环境变量 NEO4J_PASSWORD")
        sys.exit(1)
    
    try:
        # 创建初始化器
        initializer = Neo4jKnowledgeInitializer(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            database=neo4j_database
        )
        
        # 初始化知识图谱
        initializer.init_knowledge_graph()
        
        # 关闭连接
        initializer.close()
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 