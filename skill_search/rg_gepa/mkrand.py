# random-direction control: same norm as B1 at every layer, uniformly random direction
import torch, os, sys
os.chdir(os.path.expanduser("~/rg_gepa/vec"))
for b, t in (("decimal_arithmetic","qwen3-14b"),("products","qwen3-8b")):
    src = torch.load(f"out/vectors/v_{t}_{b}_B1.pt", map_location="cpu")
    for s in (1, 2):
        g = torch.Generator().manual_seed(s); vec = {}
        for l, v in src["vectors"].items():
            r = torch.randn(v.shape, generator=g, dtype=torch.float32); vec[l] = (r / r.norm() * v.float().norm()).to(v.dtype)
        os.makedirs(f"rand{s}/vectors", exist_ok=True)
        torch.save({"vectors": vec, "norm": src["norm"], "coherence": torch.zeros_like(src["coherence"]), "meta": {"arm": f"random seed {s}"}},
                   f"rand{s}/vectors/v_{t}_{b}_B1.pt")
print("ok")
