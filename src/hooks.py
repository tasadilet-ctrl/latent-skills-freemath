"""Forward hooks for reading and steering the residual stream.

Convention used throughout this project: "layer l" means the *output* of
decoder layer l (post-residual). Extraction reads there and injection writes
there, so the two are consistent by construction.
"""
from __future__ import annotations

import torch
from contextlib import contextmanager


def _get_hidden(out):
    """Qwen3_5DecoderLayer may return a Tensor or a tuple whose [0] is it."""
    if isinstance(out, tuple):
        return out[0], True
    return out, False


def _set_hidden(out, new, was_tuple):
    if was_tuple:
        return (new,) + tuple(out[1:])
    return new


@contextmanager
def capture(layers, position: int = -1, layer_ids=None):
    """Record the hidden state at `position` for each requested layer.

    Yields a dict that is populated after each forward pass:
        {layer_id: Tensor[batch, hidden]}
    Default position=-1 is the final prompt token, which is what the
    contrastive extraction in the plan specifies.
    """
    store: dict[int, torch.Tensor] = {}
    ids = range(len(layers)) if layer_ids is None else layer_ids
    handles = []

    def make(i):
        def fn(module, args, out):
            h, _ = _get_hidden(out)
            store[i] = h[:, position, :].detach().float().cpu()
        return fn

    for i in ids:
        handles.append(layers[i].register_forward_hook(make(i)))
    try:
        yield store
    finally:
        for h in handles:
            h.remove()


@contextmanager
def inject(layers, vectors: dict[int, torch.Tensor], gamma: float = 1.0,
           positions: str = "all", mode: str = "relative"):
    """Steer the residual stream: h_l <- h_l + (scaled) v_l.

    `vectors` maps layer_id -> Tensor[hidden]. Applied on every forward pass,
    so it covers both the prefill and each decode step during generation.

    mode:
      "relative" - h += gamma * ||h|| * v/||v||, per token position.
                   gamma is then "steer by this fraction of the activation
                   norm", which means the SAME gamma is comparable across
                   layers. Necessary here: the raw contrast norm runs from
                   0.4 at layer 0 to 352 at layer 63, so a single raw gamma
                   is simultaneously a no-op deep and an explosion shallow.
      "raw"      - h += gamma * v, the literal h_l + gamma*v_skill.

    positions:
      "all"  - steer every token position (standard for activation steering;
               during decode each step is a single position anyway)
      "last" - steer only the final position of whatever tensor arrives
    """
    handles = []

    def make(v):
        def fn(module, args, out):
            h, was_tuple = _get_hidden(out)
            vv = v.to(device=h.device, dtype=h.dtype)
            if mode == "relative":
                unit = vv / vv.norm().clamp(min=1e-6)
                delta = gamma * h.norm(dim=-1, keepdim=True) * unit
            elif mode == "raw":
                delta = gamma * vv
            else:
                raise ValueError(f"unknown mode={mode!r}")
            if positions == "all":
                h = h + delta
            elif positions == "last":
                h = h.clone()
                d = delta[:, -1, :] if delta.dim() == 3 else delta
                h[:, -1, :] = h[:, -1, :] + d
            else:
                raise ValueError(f"unknown positions={positions!r}")
            return _set_hidden(out, h, was_tuple)
        return fn

    for i, v in vectors.items():
        handles.append(layers[i].register_forward_hook(make(v)))
    try:
        yield
    finally:
        for h in handles:
            h.remove()
