"""SkillOpt env adapter for Reasoning Gym tasks (positive control for the MMLU-Pro SkillOpt runs)."""
from __future__ import annotations

from skillopt.datasets.base import BatchSpec
from skillopt.envs.base import EnvAdapter
from skillopt.envs.rgym.dataloader import RGymDataLoader
from skillopt.envs.rgym.rollout import run_batch


class RGymAdapter(EnvAdapter):
    def __init__(self, split_dir: str = "", data_path: str = "", split_mode: str = "split_dir",
                 split_ratio: str = "2:1:7", split_seed: int = 42, split_output_dir: str = "",
                 exec_timeout: int = 600, workers: int = 64, analyst_workers: int = 16,
                 failure_only: bool = False, minibatch_size: int = 8, edit_budget: int = 4,
                 seed: int = 42, limit: int = 0, max_completion_tokens: int = 2048, **_) -> None:
        self.exec_timeout = exec_timeout
        self.workers = workers
        self.analyst_workers = analyst_workers
        self.failure_only = failure_only
        self.minibatch_size = minibatch_size
        self.edit_budget = edit_budget
        self.max_completion_tokens = int(max_completion_tokens)
        self.dataloader = RGymDataLoader(split_dir=split_dir, data_path=data_path, split_mode=split_mode,
                                         split_ratio=split_ratio, split_seed=split_seed,
                                         split_output_dir=split_output_dir, seed=seed, limit=limit)

    def setup(self, cfg: dict) -> None:
        super().setup(cfg)
        self.dataloader.setup(cfg)

    def get_dataloader(self):
        return self.dataloader

    def build_env_from_batch(self, batch: BatchSpec, **kwargs):
        return list(batch.payload or [])

    def build_train_env(self, batch_size: int, seed: int, **kwargs):
        return self.build_env_from_batch(self.dataloader.build_train_batch(batch_size=batch_size, seed=seed, **kwargs))

    def build_eval_env(self, env_num: int, split: str, seed: int, **kwargs):
        return self.build_env_from_batch(self.dataloader.build_eval_batch(env_num=env_num, split=split, seed=seed, **kwargs))

    def rollout(self, env_manager, skill_content: str, out_dir: str, **kwargs) -> list[dict]:
        return run_batch(items=list(env_manager), out_root=out_dir, skill_content=skill_content,
                         exec_timeout=self.exec_timeout, workers=self.workers,
                         max_completion_tokens=self.max_completion_tokens)

    def get_task_types(self) -> list[str]:
        seen: list[str] = []
        for it in self.dataloader.train_items + self.dataloader.val_items + self.dataloader.test_items:
            if it["task_type"] not in seen:
                seen.append(it["task_type"])
        return seen or ["rgym"]
