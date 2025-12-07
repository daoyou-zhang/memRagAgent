from __future__ import annotations

from typing import List
import os
import sys
from concurrent.futures import ThreadPoolExecutor

# 当从 backend/knowledge 目录运行 app.py 时，默认 sys.path 中没有 backend 根目录，
# 这里显式将 backend 根目录加入 sys.path，方便复用 memory.embeddings_client。
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_ROOT not in sys.path:
  sys.path.append(BACKEND_ROOT)

from memory.embeddings_client import generate_embedding


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
  """简单的批量封装：逐条调用 memory.embeddings_client.generate_embedding。

  后续如果需要，可以在这里改成真正的批量 API 调用。
  """

  # 为了提升批量性能，这里使用受控并发方式调用 generate_embedding，
  # 保持输入输出顺序一致，同时避免过高并发压垮底层服务。
  if not texts:
    return []

  # 预分配结果列表以保证顺序
  results: List[List[float]] = [[] for _ in range(len(texts))]

  def _worker(args: tuple[int, str]) -> None:
    idx, text = args
    t_clean = (text or "").strip()
    if not t_clean:
      results[idx] = []
      return
    # 如果底层 generate_embedding 抛异常，这里让异常冒泡，
    # 由上层调用方统一处理。
    emb = generate_embedding(t_clean)
    results[idx] = emb

  # 根据批量大小和一个安全上限确定并发度
  max_workers = min(8, max(1, len(texts)))
  with ThreadPoolExecutor(max_workers=max_workers) as executor:
    # 使用 map 保证任务提交过程简单，实际顺序由 results[idx] 控制
    list(executor.map(_worker, enumerate(texts)))

  return results
