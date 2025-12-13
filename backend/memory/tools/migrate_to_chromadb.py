"""迁移 JSONB 向量到 ChromaDB

将 memories 表中的 embedding 字段迁移到 ChromaDB。
运行：python -m tools.migrate_to_chromadb
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from repository.db_session import SessionLocal
from models.memory import Memory
from services.vector_service import get_memory_vector_service


def migrate_memories():
    """迁移所有有 embedding 的记忆到 ChromaDB"""
    db = SessionLocal()
    vec_service = get_memory_vector_service()
    
    try:
        # 获取所有有向量的记忆
        memories = db.query(Memory).filter(
            Memory.embedding.isnot(None),
            Memory.type.in_(["semantic", "episodic"]),
        ).all()
        
        print(f"找到 {len(memories)} 条待迁移记忆")
        
        migrated = 0
        failed = 0
        
        for mem in memories:
            try:
                emb = mem.embedding
                if not emb or not isinstance(emb, list):
                    continue
                
                # 转换为 float 列表
                embedding = [float(x) for x in emb]
                
                success = vec_service.add_memory(
                    memory_id=mem.id,
                    text=mem.text,
                    embedding=embedding,
                    project_id=mem.project_id or "",
                    user_id=mem.user_id,
                    memory_type=mem.type,
                    importance=float(mem.importance or 0.5),
                    tags=mem.tags if isinstance(mem.tags, list) else None,
                )
                
                if success:
                    migrated += 1
                else:
                    failed += 1
                
                if migrated % 100 == 0:
                    print(f"  进度: {migrated}/{len(memories)}")
                    
            except Exception as e:
                print(f"  迁移 memory {mem.id} 失败: {e}")
                failed += 1
        
        print(f"\n✅ 迁移完成!")
        print(f"  - 成功: {migrated}")
        print(f"  - 失败: {failed}")
        
        # 打印统计
        for project_id in set(m.project_id for m in memories if m.project_id):
            stats = vec_service.get_collection_stats(project_id)
            print(f"  - {project_id}: {stats['vector_count']} 向量")
        
    finally:
        db.close()


if __name__ == "__main__":
    migrate_memories()
