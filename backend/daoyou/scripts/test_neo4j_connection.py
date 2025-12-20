#!/usr/bin/env python3
"""
Neo4j连接测试脚本

这个脚本用于测试Neo4j数据库连接是否正常。

使用方法:
    python scripts/test_neo4j_connection.py

环境变量配置:
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=your_password
    NEO4J_DATABASE=neo4j
"""

import os
import sys
from neo4j import GraphDatabase
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_neo4j_connection():
    """测试Neo4j连接"""
    # 从环境变量获取配置
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    if not neo4j_password:
        logger.error("请设置环境变量 NEO4J_PASSWORD")
        return False
    
    try:
        logger.info(f"正在连接Neo4j数据库: {neo4j_uri}")
        logger.info(f"用户名: {neo4j_user}")
        logger.info(f"数据库: {neo4j_database}")
        
        # 创建驱动
        driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        # 测试连接
        with driver.session(database=neo4j_database) as session:
            # 执行简单查询
            result = session.run("RETURN 1 as test")
            record = result.single()
            
            if record and record["test"] == 1:
                logger.info("✅ Neo4j连接测试成功！")
                
                # 检查数据库版本
                version_result = session.run("CALL dbms.components() YIELD name, versions, edition")
                version_record = version_result.single()
                if version_record:
                    logger.info(f"Neo4j版本: {version_record['name']} {version_record['versions'][0]} {version_record['edition']}")
                
                # 检查节点数量
                node_count_result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = node_count_result.single()["count"]
                logger.info(f"数据库中的节点数量: {node_count}")
                
                # 检查关系数量
                rel_count_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = rel_count_result.single()["count"]
                logger.info(f"数据库中的关系数量: {rel_count}")
                
                return True
            else:
                logger.error("❌ Neo4j连接测试失败：查询返回异常结果")
                return False
                
    except Exception as e:
        logger.error(f"❌ Neo4j连接测试失败: {e}")
        return False
    finally:
        if 'driver' in locals():
            driver.close()

def main():
    """主函数"""
    logger.info("开始测试Neo4j连接...")
    
    if test_neo4j_connection():
        logger.info("Neo4j连接测试通过！")
        sys.exit(0)
    else:
        logger.error("Neo4j连接测试失败！")
        sys.exit(1)

if __name__ == "__main__":
    main() 