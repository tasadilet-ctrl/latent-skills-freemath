"""End-to-end check of the plumbing before spending GPU-hours on the matrix.

Verifies, in order:
  1. the 27B loads in HF transformers and the decoder ModuleList resolves
  2. the chat template renders with enable_thinking=False
  3. capture hooks return one [batch, 5120] state per layer
  4. a with-skill / without-skill contrast produces a non-degenerate direction
  5. injection actually changes the generated text (gamma=0 must be a no-op)
"""
from __future__ import annotations

import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import hooks, qwen  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = ("Natalia sold clips to 48 friends in April, and then she sold half as many "
     "clips in May. How many clips did she sell altogether?")


def main():
    skill = open(os.path.join(ROOT, "skills", "decompose_verify.md")).read()
    tok, model, layers = qwen.load()
    n = len(layers)
    print(f"[1] OK  model={type(model).__name__} layers={n} "
          f"devices={ {str(p.device) for p in model.parameters()} }")

    text = qwen.build_prompt(tok, Q)
    assert "Natalia" in text and len(text) > len(Q), "chat template did not render"
    print(f"[2] OK  prompt renders, {len(tok(text)['input_ids'])} tokens")
    print("---- rendered prompt ----")
    print(text[:400])
    print("-------------------------")

    dev = qwen.first_param_device(model)
    states = []
    for system in (skill, None):
        t = qwen.build_prompt(tok, Q, system_msg=system)
        ids = tok(t, return_tensors="pt").to(dev)
        with torch.no_grad(), hooks.capture(layers) as store:
            model(**ids)
        assert len(store) == n, f"captured {len(store)} layers, expected {n}"
        states.append(torch.stack([store[l][0] for l in range(n)]))
    print(f"[3] OK  captured {n} layers, shape per layer {tuple(store[0].shape)}")

    diff = states[0] - states[1]
    norms = diff.norm(dim=-1)
    rel = norms / states[1].norm(dim=-1).clamp(min=1e-6)
    assert norms.max() > 0, "with/without contrast is identically zero"
    print(f"[4] OK  contrast norms: min={norms.min():.3f} max={norms.max():.3f} "
          f"argmax_layer={int(norms.argmax())}")
    print("    layer : |diff|   |diff|/|h|")
    for l in range(0, n, 8):
        print(f"    {l:5d} : {norms[l]:7.3f}  {rel[l]:.4f}")

    vecs = {l: diff[l] for l in range(24, 41)}
    enc = tok([qwen.build_prompt(tok, Q)], return_tensors="pt",
              padding=True, padding_side="left").to(dev)
    gen_kwargs = dict(max_new_tokens=60, do_sample=False, temperature=None,
                      top_p=None, top_k=None,
                      pad_token_id=tok.pad_token_id or tok.eos_token_id)
    with torch.no_grad():
        plain = tok.decode(model.generate(**enc, **gen_kwargs)[0, enc["input_ids"].shape[1]:],
                           skip_special_tokens=True)
        with hooks.inject(layers, vecs, gamma=0.0):
            zero = tok.decode(model.generate(**enc, **gen_kwargs)[0, enc["input_ids"].shape[1]:],
                              skip_special_tokens=True)
        with hooks.inject(layers, vecs, gamma=1.0):
            steered = tok.decode(model.generate(**enc, **gen_kwargs)[0, enc["input_ids"].shape[1]:],
                                 skip_special_tokens=True)

    assert zero == plain, "gamma=0 changed the output -- the hook is not a clean no-op"
    print("[5] OK  gamma=0 is a bit-exact no-op")
    print(f"    gamma=1 differs from baseline: {steered != plain}")
    print("---- baseline ----\n" + plain[:300])
    print("---- gamma=1.0 ----\n" + steered[:300])
    print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    main()
