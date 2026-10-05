"""OfficeQA: NEAR-AI manifest (246 questions) + gated Databricks bulletin corpus.

The question manifest is open; the Treasury Bulletin .txt files it grounds on are
gated by Databricks and must be fetched with an authenticated token. Only the
files actually referenced by the manifest are downloaded, and each is checked
against the manifest's sha256 so a silently-changed upstream cannot pass.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.parse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "officeqa_docs")
ROWS = "https://datasets-server.huggingface.co/rows"
REPO_DIR = "treasury_bulletins_parsed/transformed"


def manifest():
    out, offset = [], 0
    while True:
        q = {"dataset": "NEAR-AI/officeqa", "config": "default",
             "split": "full", "offset": offset, "length": 100}
        r = requests.get(f"{ROWS}?{urllib.parse.urlencode(q)}", timeout=120)
        r.raise_for_status()
        rows = r.json().get("rows", [])
        if not rows:
            break
        for x in rows:
            d = x["row"]
            out.append({"id": d["uid"], "question": d["question"],
                        "answer": d["answer"],
                        "source_files": json.loads(d["source_files"]),
                        "difficulty": d["difficulty"],
                        "tolerance": d["tolerance"],
                        "sha256": json.loads(d["source_file_sha256"])})
        offset += len(rows)
    return out


def main():
    from huggingface_hub import hf_hub_download
    token = os.environ.get("HF_TOKEN") or \
        open(os.path.expanduser("~/.cache/huggingface/token")).read().strip()

    rows = manifest()
    needed = sorted({f for r in rows for f in r["source_files"]})
    print(f"manifest: {len(rows)} questions referencing {len(needed)} bulletins")

    os.makedirs(CORPUS, exist_ok=True)
    sha_map = {f: s for r in rows for f, s in r["sha256"].items()}
    bad = []
    for i, fn in enumerate(needed, 1):
        dest = os.path.join(CORPUS, fn)
        if not os.path.exists(dest):
            p = hf_hub_download("databricks/officeqa", f"{REPO_DIR}/{fn}",
                                repo_type="dataset", token=token)
            with open(p, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())
        got = hashlib.sha256(open(dest, "rb").read()).hexdigest()
        if got != sha_map.get(fn):
            bad.append(fn)
        if i % 25 == 0:
            print(f"  {i}/{len(needed)}", flush=True)

    out = os.path.join(HERE, "officeqa.jsonl")
    with open(out, "w") as f:
        for r in rows:
            r.pop("sha256", None)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    sz = sum(os.path.getsize(os.path.join(CORPUS, f)) for f in needed)
    print(f"\nwrote {len(rows)} -> {out}")
    print(f"corpus: {len(needed)} files, {sz/2**20:.0f} MiB -> {CORPUS}")
    print(f"sha256 mismatches: {len(bad)}" + (f" {bad[:5]}" if bad else " (all verified)"))
    print("difficulty:", dict(Counter(r["difficulty"] for r in rows)))
    print("files per question:", dict(sorted(Counter(len(r["source_files"]) for r in rows).items())))


if __name__ == "__main__":
    main()
