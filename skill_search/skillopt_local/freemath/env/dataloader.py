"""Loader for <split dir>/{train,val,test}/items.json written by make_split_freemath.py.

Each item: {"id", "question", "answer", "task_type", "benchmark"}.
"""
from __future__ import annotations

from skillopt.datasets.base import SplitDataLoader


class FreeMathDataLoader(SplitDataLoader):
    def load_split_items(self, split_path: str) -> list[dict]:
        items = super().load_split_items(split_path)
        out = []
        for it in items:
            out.append({
                "id": str(it["id"]),
                "question": str(it["question"]).strip(),
                "answer": str(it["answer"]).strip(),
                "task_type": str(it.get("task_type") or it.get("benchmark") or "freemath"),
                "benchmark": str(it.get("benchmark") or ""),
            })
        return out
