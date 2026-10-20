"""How alike are our vectors and Rakhat's? Cosine similarity per layer, CPU only.

    python src/compare_vectors.py livemath_ts qwen3-4b qwen3-14b qwen3.6-27b
        -> printed, and record/tables/vector_cosines_<stem>.md

Ours: vectors/v_<tag>_<stem>_neutral_n50_{placebo,plain}.pt (last prompt token, neutral prompts).
Rakhat's: vectors/v_<tag>_<stem>_{replyA,replyB,stepA,stepB}.pt (src/rakhat_vectors.py).
1.00 = same direction, 0 = unrelated. In a few thousand dimensions two random
directions have |cos| around 0.02.
"""
import os
import sys

import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = ["placebo", "plain", "replyA", "replyB", "stepA", "stepB"]
LABEL = {"placebo": "ours vs placebo", "plain": "ours vs nothing", "replyA": "reply A",
         "replyB": "reply B", "stepA": "step A", "stepB": "step B"}


def load(tag, stem, name):
    suf = f"neutral_n50_{name}" if name in ("placebo", "plain") else name
    p = os.path.join(ROOT, "vectors", f"v_{tag}_{stem}_{suf}.pt")
    return torch.load(p, map_location="cpu") if os.path.exists(p) else None


def main():
    stem, tags = sys.argv[1], sys.argv[2:]
    md = [f"# Vector cosines: {stem}", "",
          "Cosine similarity between vectors, at three depths per model. "
          "1.00 = same direction; random pairs give about ±0.02.", ""]
    for tag in tags:
        vs = {n: load(tag, stem, n) for n in NAMES}
        vs = {n: v for n, v in vs.items() if v is not None}
        if len(vs) < 2:
            print(f"{tag}: missing vectors ({sorted(vs)})")
            continue
        nl = next(iter(vs.values()))["meta"]["n_layers"]
        names = [n for n in NAMES if n in vs]
        md += [f"## {tag} ({nl} layers)", ""]
        for l in sorted({nl // 2, round(nl * 0.89), nl - 2}):
            md += [f"layer {l}", "", "| | " + " | ".join(LABEL[n] for n in names) + " |",
                   "|---|" + "---|" * len(names)]
            for a in names:
                row = [f"{torch.nn.functional.cosine_similarity(vs[a]['vectors'][l].float(), vs[b]['vectors'][l].float(), dim=0).item():+.2f}"
                       for b in names]
                md.append(f"| {LABEL[a]} | " + " | ".join(row) + " |")
            md.append("")
    out = os.path.join(ROOT, "record", "tables", f"vector_cosines_{stem}.md")
    open(out, "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
