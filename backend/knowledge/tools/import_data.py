"""知识库数据批量导入工具

使用方式：
    python -m tools.import_data --collection "法律知识库" --domain law --file data/law.jsonl
    python -m tools.import_data --collection "八字命理" --domain divination --file data/bazi.jsonl --project DAOYOUTEST

JSONL 格式要求：
    {"text": "内容...", "title": "标题", "tags": ["tag1", "tag2"], ...}
    
JSON 数组格式：
    [{"text": "...", "title": "..."}, ...]
"""
import argparse
import sys
from pathlib import Path

# 添加父目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# 加载配置
backend_root = Path(__file__).parent.parent.parent
load_dotenv(backend_root / ".env")
load_dotenv()

from repository.db_session import SessionLocal
from models.knowledge import KnowledgeCollection, KnowledgeDocument, KnowledgeChunk
from processing.text_processing import TextProcessor
from processing.embedding_processing import generate_embeddings_batch


def create_or_get_collection(db, name: str, domain: str, project_id: str = None, description: str = None):
    """创建或获取集合"""
    col = db.query(KnowledgeCollection).filter(
        KnowledgeCollection.name == name,
        KnowledgeCollection.domain == domain,
    ).first()
    
    if not col:
        col = KnowledgeCollection(
            name=name,
            domain=domain,
            project_id=project_id,
            description=description,
        )
        db.add(col)
        db.commit()
        db.refresh(col)
        print(f"✓ 创建集合: {name} (id={col.id})")
    else:
        print(f"✓ 使用已有集合: {name} (id={col.id})")
    
    return col


def import_jsonl(db, file_path: Path, collection_id: int, batch_size: int = 50):
    """导入 JSONL 文件"""
    tp = TextProcessor()
    
    total_chunks = 0
    total_docs = 0
    
    records = list(tp.iter_jsonl_records(file_path))
    print(f"读取 {len(records)} 条记录")
    
    for i, obj in enumerate(records):
        text = str(obj.get("text") or "").strip()
        if not text:
            continue
        
        title = obj.get("title") or f"doc_{i}"
        
        # 创建文档
        doc = KnowledgeDocument(
            collection_id=collection_id,
            title=title,
            source_uri=str(file_path),
            extra_metadata={k: v for k, v in obj.items() if k not in ["text"]},
            status="pending",
        )
        db.add(doc)
        db.flush()
        total_docs += 1
        
        # 分块
        chunks = tp.chunk_text(tp.clean_text(text))
        if not chunks:
            continue
        
        # 生成 embedding
        embeddings = generate_embeddings_batch(chunks)
        
        # 写入 chunks
        for idx, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
            ch = KnowledgeChunk(
                document_id=doc.id,
                chunk_index=idx,
                section_label=obj.get("article_no") or obj.get("section"),
                text=chunk_text,
                tags=obj.get("tags"),
                embedding=emb,
                importance=0.5,
                extra_metadata={
                    "source_file": file_path.name,
                    "domain": obj.get("domain"),
                    "type": obj.get("type"),
                },
            )
            db.add(ch)
            total_chunks += 1
        
        doc.status = "indexed"
        
        # 定期提交
        if (i + 1) % batch_size == 0:
            db.commit()
            print(f"  进度: {i + 1}/{len(records)} 文档, {total_chunks} 块")
    
    db.commit()
    return total_docs, total_chunks


def import_json_array(db, file_path: Path, collection_id: int, batch_size: int = 50):
    """导入 JSON 数组文件"""
    tp = TextProcessor()
    
    records = tp.load_json_array(file_path)
    if not records:
        print("JSON 文件为空或格式不正确")
        return 0, 0
    
    print(f"读取 {len(records)} 条记录")
    
    total_chunks = 0
    total_docs = 0
    
    for i, obj in enumerate(records):
        text = str(obj.get("text") or "").strip()
        if not text:
            continue
        
        title = obj.get("title") or f"doc_{i}"
        
        doc = KnowledgeDocument(
            collection_id=collection_id,
            title=title,
            source_uri=str(file_path),
            extra_metadata={k: v for k, v in obj.items() if k not in ["text"]},
            status="pending",
        )
        db.add(doc)
        db.flush()
        total_docs += 1
        
        chunks = tp.chunk_text(tp.clean_text(text))
        if not chunks:
            continue
        
        embeddings = generate_embeddings_batch(chunks)
        
        for idx, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
            ch = KnowledgeChunk(
                document_id=doc.id,
                chunk_index=idx,
                section_label=obj.get("article_no") or obj.get("section"),
                text=chunk_text,
                tags=obj.get("tags"),
                embedding=emb,
                importance=0.5,
                extra_metadata={
                    "source_file": file_path.name,
                },
            )
            db.add(ch)
            total_chunks += 1
        
        doc.status = "indexed"
        
        if (i + 1) % batch_size == 0:
            db.commit()
            print(f"  进度: {i + 1}/{len(records)} 文档, {total_chunks} 块")
    
    db.commit()
    return total_docs, total_chunks


def main():
    parser = argparse.ArgumentParser(description="知识库数据导入工具")
    parser.add_argument("--collection", "-c", required=True, help="集合名称")
    parser.add_argument("--domain", "-d", required=True, help="领域 (law/divination/medical/general)")
    parser.add_argument("--file", "-f", required=True, help="数据文件路径 (JSONL 或 JSON)")
    parser.add_argument("--project", "-p", default=None, help="项目 ID")
    parser.add_argument("--description", default=None, help="集合描述")
    parser.add_argument("--batch-size", "-b", type=int, default=50, help="批处理大小")
    
    args = parser.parse_args()
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        sys.exit(1)
    
    db = SessionLocal()
    try:
        # 创建或获取集合
        col = create_or_get_collection(
            db=db,
            name=args.collection,
            domain=args.domain,
            project_id=args.project,
            description=args.description,
        )
        
        # 根据文件类型导入
        ext = file_path.suffix.lower()
        if ext == ".jsonl":
            docs, chunks = import_jsonl(db, file_path, col.id, args.batch_size)
        elif ext == ".json":
            docs, chunks = import_json_array(db, file_path, col.id, args.batch_size)
        else:
            print(f"❌ 不支持的文件格式: {ext}")
            sys.exit(1)
        
        print(f"\n✓ 导入完成!")
        print(f"  - 集合: {col.name} (id={col.id})")
        print(f"  - 文档: {docs}")
        print(f"  - 块数: {chunks}")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
