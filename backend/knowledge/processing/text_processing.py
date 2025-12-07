from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import json
import re

import pandas as pd


class TextProcessor:
    """轻量文本处理器，用于知识库索引。

    支持：txt / pdf / doc / docx / xlsx / xls / csv / json / jsonl。
    其中 json/jsonl 更偏向“记录级文本”，由上游决定字段含义。
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # ---- 通用步骤 ----

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text.strip())
        # 保守清洗：保留中英文、数字和常见标点
        text = re.sub(r"[^\u4e00-\u9fff\w\s.,!?;:()（）【】\[\]""''、。，！？；：]", "", text)
        text = re.sub(r"[。，！？；：]{2,}", lambda m: m.group()[0], text)
        return text

    def chunk_text(self, text: str) -> List[str]:
        if not text:
            return []

        separators = ["\n\n", "\n", "。", "，", " "]

        def _recursive_split(text_to_split: str, seps: List[str]) -> List[str]:
            if not text_to_split:
                return []
            if len(text_to_split) <= self.chunk_size:
                return [text_to_split]
            if not seps:
                return [
                    text_to_split[i : i + self.chunk_size]
                    for i in range(0, len(text_to_split), self.chunk_size)
                ]

            current_separator = seps[0]
            remaining = seps[1:]
            splits = text_to_split.split(current_separator)

            results: List[str] = []
            current_chunk = ""
            for part in splits:
                if not part:
                    continue
                if len(current_chunk) + len(part) > self.chunk_size and current_chunk:
                    results.extend(_recursive_split(current_chunk, remaining))
                    current_chunk = part
                else:
                    if current_chunk:
                        current_chunk += current_separator + part
                    else:
                        current_chunk = part

            if current_chunk:
                results.extend(_recursive_split(current_chunk, remaining))
            return results

        initial_chunks = _recursive_split(text, separators)

        # 处理 overlap
        if self.chunk_overlap > 0 and len(initial_chunks) > 1:
            final_chunks: List[str] = []
            for i, chunk in enumerate(initial_chunks):
                if i == 0:
                    final_chunks.append(chunk)
                    continue
                prev = initial_chunks[i - 1]
                overlap = prev[-self.chunk_overlap :]
                final_chunks.append((overlap + chunk).strip())
            return [c for c in final_chunks if c]
        return [c for c in initial_chunks if c]

    # ---- 文件级处理 ----

    def extract_text_from_file(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()
        try:
            if ext == ".txt":
                return file_path.read_text(encoding="utf-8", errors="ignore")
            if ext == ".json":
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._json_to_text(data)
            if ext in {".xlsx", ".xls"}:
                df = pd.read_excel(file_path)
                return self._df_to_text(df)
            if ext == ".csv":
                df = pd.read_csv(file_path)
                return self._df_to_text(df)
        except Exception:
            return ""
        # 其他格式未来有需要再补 PDF/Word；当前若不支持则返回空
        return ""

    def _json_to_text(self, data: Any) -> str:
        if isinstance(data, dict):
            lines = []
            for k, v in data.items():
                lines.append(f"{k}: {self._json_to_text(v)}")
            return "\n".join(lines)
        if isinstance(data, list):
            return "\n".join(self._json_to_text(x) for x in data)
        return str(data)

    def _df_to_text(self, df: pd.DataFrame) -> str:
        texts: List[str] = []
        for _, row in df.iterrows():
            parts = [str(v) for v in row.values if pd.notna(v)]
            if parts:
                texts.append(" ".join(parts))
        return "\n".join(texts)

    # ---- 顶层 API ----

    def process_plain_document(self, file_path: Path) -> Dict[str, Any]:
        """针对非 JSON/JSONL 文档：整体抽取 → 清洗 → 分块。"""
        raw_text = self.extract_text_from_file(file_path)
        if not raw_text:
            return {"chunks": [], "metadata": {}}
        cleaned = self.clean_text(raw_text)
        chunks = self.chunk_text(cleaned)
        meta = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_extension": file_path.suffix,
            "total_chunks": len(chunks),
            "total_characters": len(cleaned),
        }
        return {"chunks": chunks, "metadata": meta}

    def iter_jsonl_records(self, file_path: Path) -> List[Dict[str, Any]]:
        """读取 JSONL，返回每条记录（已解析为 dict）。"""
        records: List[Dict[str, Any]] = []
        with file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    records.append(obj)
        return records

    def load_json_array(self, file_path: Path) -> List[Dict[str, Any]]:
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        return []
