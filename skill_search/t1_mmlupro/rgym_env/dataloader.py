"""Loader for <split dir>/{train,val}/items.json written by make_rg_split.py (Reasoning Gym tasks).

Each item: {"id", "question", "answer", "task", "seed", "idx", "size"}; the full Reasoning Gym entry is
regenerated from (task, size, seed, idx) when scoring. RGYM_VAL_REPEATS=K (default 1) lists every validation
question K times (ids <id>#r0..), so the acceptance score is the mean over K samples per question.
"""
from __future__ import annotations

import dataclasses
import os

from skillopt.datasets.base import SplitDataLoader


class RGymDataLoader(SplitDataLoader):
    def load_split_items(self, split_path: str) -> list[dict]:
        items = super().load_split_items(split_path)
        return [{"id": str(it["id"]), "question": str(it["question"]), "answer": str(it["answer"]),
                 "task": it["task"], "seed": int(it["seed"]), "idx": int(it["idx"]), "size": int(it["size"]),
                 "task_type": it["task"]} for it in items]

    def build_eval_batch(self, env_num: int, split: str, seed: int, **kwargs):
        batch = super().build_eval_batch(env_num=env_num, split=split, seed=seed, **kwargs)
        k = int(os.environ.get("RGYM_VAL_REPEATS", "1") or 1)
        if k > 1 and split in ("valid_seen", "val", "valid", "selection"):
            items = [dict(it, id=f"{it['id']}#r{j}") for j in range(k) for it in (batch.payload or [])]
            print(f"  [rgym] validation x{k}: {len(items)} rollouts")
            batch = dataclasses.replace(batch, payload=items, batch_size=len(items))
        return batch
