"""Model loading + module resolution for Qwen3.6-27B (Qwen3_5ForConditionalGeneration).

The checkpoint is multimodal, so the text decoder is nested at
`model.language_model.layers.N` rather than the usual `model.layers.N`.
We resolve it structurally instead of hard-coding the path.
"""
from __future__ import annotations

import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen3.6-27B")


def model_tag(model_id: str | None = None) -> str:
    """Short filesystem-safe name for the active model.

    Every artefact (vectors, results) is named with this. Without it a
    Qwen3-8B run and a Qwen3.6-27B run write the same filename and the second
    silently destroys the first -- which is exactly the comparison we are here
    to make.
    """
    return (model_id or MODEL_ID).split("/")[-1].lower()


def find_decoder_layers(model) -> torch.nn.ModuleList:
    """Return the ModuleList holding the text decoder layers.

    Picks the longest ModuleList whose elements are *DecoderLayer, which
    excludes the vision blocks and the 1-layer MTP head.
    """
    best_name, best = None, None
    for name, mod in model.named_modules():
        if isinstance(mod, torch.nn.ModuleList) and len(mod) > 0:
            if "DecoderLayer" in type(mod[0]).__name__:
                if best is None or len(mod) > len(best):
                    best_name, best = name, mod
    if best is None:
        raise RuntimeError("could not locate decoder layers in %s" % type(model).__name__)
    return best


def preflight(min_free_gb: float = 20.0):
    """Fail fast if the assigned GPU is already occupied.

    This cluster has jobs that use GPU memory without requesting it through
    SLURM, so an allocation is no guarantee the card is actually free. Without
    this check, device_map="auto" silently offloads most of the model to CPU and
    the run dies with an opaque OOM deep inside a forward pass, minutes later.
    """
    if not torch.cuda.is_available():
        raise RuntimeError("no CUDA device visible")
    for i in range(torch.cuda.device_count()):
        free, total = torch.cuda.mem_get_info(i)
        free_gb, total_gb = free / 2**30, total / 2**30
        print(f"[preflight] cuda:{i} {free_gb:.1f}/{total_gb:.1f} GiB free", flush=True)
        if free_gb < min_free_gb:
            raise RuntimeError(
                f"cuda:{i} has only {free_gb:.1f} GiB free of {total_gb:.1f} "
                f"(need >= {min_free_gb}). Another process is occupying this GPU "
                f"outside SLURM's accounting; resubmit or exclude this node.")


def load(dtype=torch.bfloat16, device_map="auto", attn_implementation=None,
         min_free_gb: float = 20.0):
    preflight(min_free_gb)
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    kwargs = dict(dtype=dtype, device_map=device_map, low_cpu_mem_usage=True)
    if attn_implementation:
        kwargs["attn_implementation"] = attn_implementation
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, **kwargs)
    if tok.pad_token_id is None:
        # Qwen ships no pad token; batched left-padding in evaluate.py needs one.
        tok.pad_token = tok.eos_token
    model.eval()
    layers = find_decoder_layers(model)
    return tok, model, layers


def build_prompt(tok, user_msg: str, system_msg: str | None = None,
                 enable_thinking: bool = False) -> str:
    """Render a single-turn chat prompt ending at the generation cue.

    enable_thinking defaults to False: <think> blocks are long and variable,
    which would make the with-skill / without-skill activation contrast noisy
    and the 4-quadrant scores incomparable across conditions.
    """
    msgs = []
    if system_msg:
        msgs.append({"role": "system", "content": system_msg})
    msgs.append({"role": "user", "content": user_msg})
    return tok.apply_chat_template(
        msgs, tokenize=False, add_generation_prompt=True,
        enable_thinking=enable_thinking,
    )


def first_param_device(module) -> torch.device:
    return next(module.parameters()).device
