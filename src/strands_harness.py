"""Strands-SDK agent harness -- the replacement for the OpenHands agent loop.

Ported from RakhatMM/asr-autoadapt @ branch `strands_harness`, release
harness-v2.2 (commit of 2026-09-25). The Agent / OpenAIModel / hook /
SequentialToolExecutor construction follows harness/loop.py and
harness/strands_glue.py there.

That harness drives typed domain tools (train/acquire/eval). The latent-skills
agents instead need a shell and a file editor, so this module binds the SDK's
own vended `shell` and `file_editor` to a sandbox pinned at a per-task
workspace.

Uses strands.vended_tools, NOT the separate strands-agents-tools package --
the latter's shell/editor are deprecated as of 0.8.9 ("becomes an error log in
v0.9.0") and bypass the sandbox abstraction entirely.

WHAT CHANGED VERSUS OPENHANDS -- READ BEFORE COMPARING NUMBERS
--------------------------------------------------------------
OpenHands shipped `terminal` and `file_editor` as first-class tools with its
own prompting and error surfaces. Strands' equivalents are close but not
identical in tool name, description, argument shape or error text -- all of
which the model sees. The agent's capability surface therefore differs
between harnesses.

Consequence: SpreadsheetBench / OfficeQA results produced here are NOT
directly comparable to the OpenHands cells already in results/. Compare
conditions WITHIN a harness; treat the harness as a factor. Summaries written
by the adapters carry "harness": "strands" so src/matrix.py keeps them apart.

Deliberate equivalences to the OpenHands loop:
    AgentContext(system_message_suffix=skill)  ->  system_prompt + "\n\n" + skill
    Conversation(workspace=d)                  ->  WorkspaceEnvironment(d)
    max_iteration_per_run=N                    ->  IterationCap hook
    stuck_detection=on                         ->  NoProgressStop hook
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, AsyncGenerator

from strands import Agent
from strands.agent.conversation_manager import NullConversationManager
from strands.hooks import (HookProvider, HookRegistry,
                           BeforeModelCallEvent, AfterToolCallEvent)
from strands.models.openai import OpenAIModel
from strands.sandbox.not_a_sandbox_local_environment import (
    NotASandboxLocalEnvironment)
from strands.tools.executors import SequentialToolExecutor
from strands.types.exceptions import EventLoopException
from strands.vended_tools import make_file_editor, make_shell


class EpisodeOver(Exception):
    """Raised from a hook to end an episode (budget spent, or no progress)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class WorkspaceEnvironment(NotASandboxLocalEnvironment):
    """Local execution pinned to one task directory.

    This is what reproduces OpenHands' Conversation(workspace=...): shards run
    concurrently against the same benchmark, so an agent that resolved a
    relative path against the process cwd would read and overwrite another
    shard's workbook. Both the shell cwd and the file-operation path
    resolution are forced here, so the pinning does not depend on the model
    cooperating.

    No isolation beyond that -- commands run as this user, same as under the
    previous harness.
    """

    def __init__(self, root: str):
        self.root = Path(os.path.realpath(root))

    def _resolve_path(self, path: str) -> Path:
        # Normalise LEXICALLY (abspath), not with resolve(): the OfficeQA
        # adapter symlinks each question's bulletins into the workspace, and
        # resolve() would follow those links out to the shared docs directory
        # and have every read refused as an escape. abspath still collapses
        # '..' so the guard below holds.
        joined = path if os.path.isabs(path) else os.path.join(str(self.root), path)
        q = Path(os.path.abspath(joined))
        if q != self.root and self.root not in q.parents:
            raise ValueError(f"path escapes the task workspace: {path}")
        return q

    async def execute_streaming(self, command: str, *, cwd: str | None = None,
                                **kwargs: Any) -> AsyncGenerator[Any, None]:
        async for chunk in super().execute_streaming(
                command, cwd=str(self.root), **kwargs):
            yield chunk


class IterationCap(HookProvider):
    """OpenHands' max_iteration_per_run. One iteration == one model call."""

    def __init__(self, limit: int):
        self.limit = limit
        self.model_calls = 0
        self.tool_calls = 0

    def register_hooks(self, registry: HookRegistry, **_):
        registry.add_callback(BeforeModelCallEvent, self._before_model)
        registry.add_callback(AfterToolCallEvent, self._after_tool)

    def _before_model(self, _event):
        self.model_calls += 1
        if self.model_calls > self.limit:
            raise EpisodeOver("iteration_cap")

    def _after_tool(self, _event):
        self.tool_calls += 1


class NoProgressStop(HookProvider):
    """Stand-in for OpenHands stuck_detection: stop after `limit` consecutive
    failing tool calls. Deliberately dumber than OpenHands' detector -- it
    only catches a hard loop, so a weak model retrying legitimately is not cut
    off early (a real failure mode on Qwen3-8B under the old harness)."""

    def __init__(self, limit: int = 6):
        self.limit = limit
        self.consecutive_errors = 0

    def register_hooks(self, registry: HookRegistry, **_):
        registry.add_callback(AfterToolCallEvent, self._after_tool)

    def _after_tool(self, event):
        result = getattr(event, "result", None)
        status = result.get("status") if isinstance(result, dict) else None
        if status == "error":
            self.consecutive_errors += 1
            if self.consecutive_errors >= self.limit:
                raise EpisodeOver("stuck")
        else:
            self.consecutive_errors = 0


def make_model(model_id: str, base_url: str, api_key: str = "sk-anything",
               params: dict | None = None) -> OpenAIModel:
    """Long timeout + client-side retries, as in asr-autoadapt harness/loop.py:
    concurrent shards share one vLLM endpoint, and a queued request must not
    kill an episode."""
    return OpenAIModel(
        client_args={"base_url": base_url, "api_key": api_key,
                     "timeout": 1800.0, "max_retries": 5},
        model_id=model_id, params=dict(params or {}))


def run_episode(model, system_prompt: str, message: str, workspace: str,
                max_iterations: int = 15,
                stuck_detection: bool = True) -> dict:
    """Run one task to completion. Returns
    {reason, model_calls, tool_calls, error}.

    Never raises for agent-side failure -- the caller scores the workspace,
    exactly as the OpenHands adapters did.
    """
    sandbox = WorkspaceEnvironment(workspace)
    cap = IterationCap(max_iterations)
    hooks = [cap] + ([NoProgressStop()] if stuck_detection else [])
    agent = Agent(model=model,
                  sandbox=sandbox,
                  tools=[make_shell(sandbox=sandbox),
                         make_file_editor(sandbox=sandbox)],
                  hooks=hooks,
                  system_prompt=system_prompt,
                  conversation_manager=NullConversationManager(),
                  # sequential, not the SDK's concurrent default: the agent
                  # edits one workbook and parallel writes race on it
                  tool_executor=SequentialToolExecutor(),
                  callback_handler=None)
    reason, err = "completed", None
    try:
        agent(message)
    except EventLoopException as wrapped:        # strands wraps hook raises
        inner = getattr(wrapped, "original_exception", None)
        if isinstance(inner, EpisodeOver):
            reason = inner.reason
        else:
            e = inner or wrapped
            reason, err = "error", f"{type(e).__name__}: {str(e)[:200]}"
    except EpisodeOver as e:
        reason = e.reason
    except Exception as e:                        # noqa: BLE001
        reason, err = "error", f"{type(e).__name__}: {str(e)[:200]}"
    return {"reason": reason, "model_calls": cap.model_calls,
            "tool_calls": cap.tool_calls, "error": err}
