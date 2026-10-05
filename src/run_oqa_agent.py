"""OfficeQA through the same Strands agent used for SpreadsheetBench.

The documents cannot be put in the prompt: the bulletins a single question
references total ~215k tokens at the median, 534k at p90 and 1.2M at worst.
Zero of the 246 questions fit an 8B/14B context and only 58% fit the 27B. So
the agent is given the files on disk and a terminal, and greps for what it
needs -- which is how the benchmark is meant to be used, and makes context
length irrelevant.

Only the files a question actually references are linked into its workspace.
Exposing all 285 bulletins would turn the task into corpus search, which is a
different (and much harder) task than the benchmark scores.

Grading is numeric with the per-question tolerance from the manifest, falling
back to normalised string equality for non-numeric answers.

Conditions match the other benchmarks: baseline / text, with the skill
appended to a mechanics prompt that is byte-identical across arms. The harness
is the Strands SDK (src/strands_harness.py), which replaced OpenHands on
2026-10-05; the old adapter is kept verbatim in legacy_openhands/. The two
harnesses do not expose identical tools, so numbers from this script are NOT
comparable to the OpenHands cells in results/. The embed arm needs
src/serve_hooked.py behind LLM_BASE_URL; nothing here changes for it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DOCS = os.path.join(DATA, "officeqa_docs")

# Bulletins whose sha256 did not match the manifest -- upstream changed them
# after the manifest was written, so questions grounded on them are excluded.
BAD_FILES = {"treasury_bulletin_1970_03.txt", "treasury_bulletin_1975_04.txt",
             "treasury_bulletin_1977_03.txt", "treasury_bulletin_1997_03.txt"}

# Both arms get this. MECHANICS only -- what the tools are and what counts as
# done -- with no advice on how to search a document, so the skill under test
# is the only procedural content that varies. OpenHands supplied an equivalent
# prompt of its own; Strands supplies none, so it is written out here.
MECHANICS = """You are working in a Linux workspace.

You have two tools:
  shell        run a shell command in the workspace
  file_editor  view or edit a file in the workspace

grep, awk and Python are available. The workspace is your working directory;
relative paths resolve against it.

Work until the task is done, then stop. Do not ask the user questions -- there
is nobody to answer them."""

TASK = """The files in your working directory are US Treasury Bulletins in plain text.

Question: {question}

Find the answer in the documents. They are large, so search rather than read
them end to end -- grep is available and so is Python.

Files available: {files}

When you have the answer, WRITE IT TO A FILE called `answer.txt` in the
working directory, containing nothing but the value itself. For numeric
answers give a bare number: no units, no thousands separators, no currency
symbol. Creating `answer.txt` is how you finish the task."""


def load_questions(limit, include_tainted=False):
    rows = [json.loads(l) for l in open(os.path.join(DATA, "officeqa.jsonl"))]
    out = []
    for r in rows:
        if not include_tainted and (BAD_FILES & set(r["source_files"])):
            continue
        if all(os.path.exists(os.path.join(DOCS, f)) for f in r["source_files"]):
            out.append(r)
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- grading --

_NUM = re.compile(r"-?[\d,]*\.?\d+")


def to_num(s):
    if s is None:
        return None
    t = str(s).strip().replace(",", "").replace("$", "").replace("%", "")
    m = _NUM.search(t)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def extract_answer(text):
    m = re.findall(r"ANSWER:\s*(.+)", text or "", re.I)
    if m:
        return m[-1].strip()
    lines = [l.strip() for l in (text or "").strip().split("\n") if l.strip()]
    return lines[-1] if lines else ""


def grade(pred_raw, gold, tol):
    """Numeric within tolerance, else normalised string equality."""
    pred = extract_answer(pred_raw)
    g, p = to_num(gold), to_num(pred)
    if g is not None and p is not None:
        try:
            t = float(tol) if tol not in (None, "") else 0.01
        except (TypeError, ValueError):
            t = 0.01
        # manifest tolerances are relative (e.g. 0.01 == 1%)
        return float(abs(p - g) <= abs(g) * t + 1e-9), pred
    norm = lambda s: re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()
    return float(norm(pred) == norm(gold)), pred


# ------------------------------------------------------------------- main --

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=["baseline", "text"], required=True)
    ap.add_argument("--skill", default=os.path.join(ROOT, "skills", "officeqa_lookup.md"))
    ap.add_argument("--limit", type=int, default=239)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--max-iterations", type=int, default=25)
    ap.add_argument("--include-tainted", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    import importlib.metadata as _md
    from src import strands_harness as S
    sdk_version = _md.version("strands-agents")

    base_url = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:9000")
    # Ask the SERVER whether it is steering. An embed run passes
    # --condition baseline (there is no skill TEXT), so without this the
    # summary is indistinguishable from a true baseline -- and a stale embed
    # file then merges into the baseline cell and corrupts it, which is
    # exactly what happened on 2026-09-28.
    steering = None
    try:
        import urllib.request
        h = json.load(urllib.request.urlopen(
            base_url.rstrip("/").removesuffix("/v1") + "/health", timeout=10))
        if h.get("steering") and h["steering"] != "none":
            steering = h["steering"]
    except Exception:
        pass
    if steering:
        print(f"[run] SERVER IS STEERING: {steering}", flush=True)
    # Strands' OpenAIModel takes a bare model id, not a litellm provider route.
    model_id = os.environ.get("LLM_MODEL", "qwen3.6-27b").split("/")[-1]
    model = S.make_model(model_id=model_id, base_url=base_url,
                         api_key=os.environ.get("LLM_API_KEY", "sk-anything"))
    rows = load_questions(args.limit, args.include_tainted)
    i, k = (int(x) for x in args.shard.split("/"))
    rows = rows[i::k]
    print(f"[oqa] {args.condition} via {base_url} model={model_id} "
          f"harness=strands-{sdk_version}", flush=True)
    print(f"[oqa] {len(rows)} questions, shard {i}/{k}", flush=True)

    skill_text = open(args.skill).read() if args.condition == "text" else None
    system_prompt = MECHANICS + ("\n\n" + skill_text if skill_text else "")

    records, t0, stops = [], time.time(), {}
    for n, r in enumerate(rows, 1):
        d = tempfile.mkdtemp(prefix="oqa-")
        ok, pred, note = 0.0, "", ""
        try:
            # symlink only this question's sources: exposing all 285 bulletins
            # would make it a corpus-search task the benchmark does not score
            for f in r["source_files"]:
                os.symlink(os.path.join(DOCS, f), os.path.join(d, f))
            ep = S.run_episode(
                model, system_prompt,
                TASK.format(question=r["question"].strip(),
                            files=", ".join(r["source_files"])),
                workspace=d, max_iterations=args.max_iterations)
            stops[ep["reason"]] = stops.get(ep["reason"], 0) + 1
            # Read the answer off DISK. Parsing it out of the conversation
            # event log needs the SDK's typed-event internals and silently
            # yielded nothing for 239/239 questions on the first attempt;
            # a file the agent writes is unambiguous.
            ap_ = os.path.join(d, "answer.txt")
            text = ""
            if os.path.exists(ap_):
                text = open(ap_, errors="replace").read().strip()[:400]
            else:
                note = ep["error"] or f"no answer.txt ({ep['reason']})"
            ok, pred = grade(text, r["answer"], r.get("tolerance")) if text else (0.0, "")
        except Exception as e:
            note = f"{type(e).__name__}: {str(e)[:140]}"
        finally:
            shutil.rmtree(d, ignore_errors=True)
        records.append({"id": r["id"], "gold": str(r["answer"]),
                        "pred": pred or note or "(none)", "em": ok, "f1": ok,
                        "difficulty": r.get("difficulty"),
                        "n_files": len(r["source_files"]), "raw": note})
        if n % 5 == 0 or n == len(rows):
            print(f"[oqa] {n}/{len(rows)}  acc={sum(x['em'] for x in records)/len(records)*100:.1f}%"
                  f"  ({time.time()-t0:.0f}s)", flush=True)

    nn = len(records)
    em = sum(r["em"] for r in records) / nn
    tag = os.environ.get("MODEL_TAG", "qwen3.6-27b")
    summary = {"domain": "officeqa",
               "condition": "embed" if steering else args.condition, "n": nn,
               "model": model_id, "model_tag": tag,
               "harness": "strands", "sdk": "strands-agents",
               "sdk_version": sdk_version, "stop_reasons": stops,
               "skill": os.path.basename(args.skill) if skill_text else None,
               "em": em, "f1": em, "seconds": round(time.time() - t0, 1),
               "parse_rate": 1.0, "forced": 0, "forced_rate": 0.0,
               "mean_pred_chars": 0.0, "max_new_tokens": 0,
               "max_iterations": args.max_iterations,
               "vector": ({"file": steering.split()[0], "steering": steering,
                           "layers": [-1], "gamma": -1.0, "pool": "server",
                           "mode": "relative"} if steering else {}),
               "shard": args.shard}
    name = args.tag or f"officeqa_{tag}_{args.condition}"
    if skill_text:
        name += "_" + os.path.basename(args.skill).replace(".md", "")
    name += f"_s{i}of{k}"
    out = os.path.join(ROOT, "results", f"{name}.json")
    with open(out, "w") as f:
        json.dump({"summary": summary, "records": records}, f, indent=2)
    print(json.dumps(summary, indent=2), flush=True)
    print(f"[oqa] wrote {out}", flush=True)


if __name__ == "__main__":
    main()
