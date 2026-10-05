"""SpreadsheetBench runner: instruction + workbook -> openpyxl script -> graded .xlsx.

Same three conditions as evaluate.py (baseline / text / embed), so the skill
comparison is identical in shape; only the task format differs. The embedding
arm needs HF `transformers` with forward hooks, so generation is single-turn
code emission rather than a multi-turn agent loop -- a tool-calling agent would
still work with hooks, but every extra turn multiplies the wall-clock of a cell
that already costs GPU-hours, and it is not needed to pose the task.

Two deliberate deviations from the official SpreadsheetBench protocol, both
applied identically in every condition so they cannot bias the comparison:

  1. The model is asked for COMPUTED LITERAL VALUES, not formulas. This node has
     no LibreOffice and no recalculation library, so a written formula has no
     cached value and `openpyxl(data_only=True)` reads it back as None -- every
     formula answer would score zero regardless of correctness.
  2. The answer location (sheet + range) is given in the prompt. The grader
     checks exactly that region, and many instructions only gesture at it, so
     withholding it would score navigation rather than the task.

Generated code is executed. There is no container on this cluster, so the
mitigations are: a private temp directory as cwd, no shell, a hard timeout, and
a static reject-list for calls a spreadsheet edit never needs. That is
defence-in-depth, not a sandbox -- do not run this on untrusted model output.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import grade_spreadsheet as G  # noqa: E402
from src import hooks, qwen  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "spreadsheetbench_verified_400")

MAX_ROWS, MAX_COLS, MAX_CHARS = 60, 20, 6000
TIMEOUT_S = 60

# Calls a spreadsheet edit never needs. Not a security boundary -- a determined
# generation gets around a regex -- but it catches the plausible accidents
# (a model "cleaning up" with rmtree, or trying to pip install a helper).
FORBIDDEN = re.compile(
    r"\b(os\.system|os\.popen|os\.remove|os\.rmdir|os\.unlink|subprocess|"
    r"shutil\.rmtree|socket|requests|urllib|ftplib|smtplib|pip|"
    r"__import__\s*\(\s*['\"]os|eval\s*\(|exec\s*\()", re.I)

PROMPT = """You are editing an Excel workbook with Python and openpyxl.

## Task
{instruction}

## Workbook `input.xlsx`
{rendering}

## Where the answer goes
Sheet: {sheet}
Range: {rng}

## What to write
Return one Python script in a ```python code block. It must:
- open `input.xlsx` with openpyxl
- perform the task above
- write **computed literal values, not formulas** into the answer range
  (a formula would be stored without a cached value and read back as empty)
- save the result as `output.xlsx`

Return only the code block."""


# ------------------------------------------------------------- rendering ----

def render_workbook(path: str) -> str:
    import openpyxl
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception as e:
        return f"(could not read workbook: {type(e).__name__})"
    out, total = [], 0
    for ws in wb.worksheets:
        head = (f"### Sheet {ws.title!r}  "
                f"({ws.max_row} rows x {ws.max_column} cols)")
        out.append(head)
        total += len(head)
        rows = []
        for r in range(1, min(ws.max_row, MAX_ROWS) + 1):
            cells = []
            for c in range(1, min(ws.max_column, MAX_COLS) + 1):
                v = ws.cell(r, c).value
                cells.append("" if v is None else str(v)[:40])
            line = f"{r}: " + " | ".join(cells).rstrip(" |")
            rows.append(line)
            total += len(line)
            if total > MAX_CHARS:
                rows.append("... (truncated)")
                break
        out.append("\n".join(rows))
        if ws.max_row > MAX_ROWS or ws.max_column > MAX_COLS:
            out.append(f"... (showing first {MAX_ROWS} rows x {MAX_COLS} cols)")
        if total > MAX_CHARS:
            out.append("... (remaining sheets omitted)")
            break
    return "\n".join(out)


def build_question(task: dict, init_path: str) -> str:
    return PROMPT.format(
        instruction=task["instruction"].strip(),
        rendering=render_workbook(init_path),
        sheet=task.get("answer_sheet") or "(the active sheet)",
        rng=task["answer_position"])


# --------------------------------------------------------------- running ----

CODE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def extract_code(text: str) -> str | None:
    m = CODE_RE.findall(text)
    if m:
        return max(m, key=len).strip()
    # unfenced fallback: a reply that starts straight into an import
    if "import openpyxl" in text:
        return text[text.index("import openpyxl"):].strip()
    return None


def run_script(code: str, init_path: str) -> tuple[str | None, str]:
    """Execute in a private temp dir. Returns (produced_path_or_None, note)."""
    if code is None:
        return None, "no code block in reply"
    bad = FORBIDDEN.search(code)
    if bad:
        return None, f"rejected: forbidden call {bad.group(0)!r}"
    d = tempfile.mkdtemp(prefix="sb-")
    try:
        shutil.copy(init_path, os.path.join(d, "input.xlsx"))
        with open(os.path.join(d, "s.py"), "w") as f:
            f.write(code)
        env = dict(os.environ, PYTHONPATH=os.environ.get("PYTHONPATH", ""))
        p = subprocess.run([sys.executable, "s.py"], cwd=d, env=env,
                           capture_output=True, text=True, timeout=TIMEOUT_S)
        out = os.path.join(d, "output.xlsx")
        if not os.path.exists(out):
            err = (p.stderr or p.stdout or "").strip().splitlines()
            return None, "no output.xlsx; " + (err[-1][:160] if err else "no error output")
        # Copy OUT of the temp dir (the finally-block removes it) and keep the
        # .xlsx suffix -- openpyxl validates the extension before reading.
        fd, keep = tempfile.mkstemp(prefix="sb-out-", suffix=".xlsx")
        os.close(fd)
        shutil.copy(out, keep)
        return keep, ""
    except subprocess.TimeoutExpired:
        return None, f"timeout after {TIMEOUT_S}s"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    finally:
        shutil.rmtree(d, ignore_errors=True)


@torch.no_grad()
def generate(tok, model, prompts, max_new, bs):
    outs = []
    dev = qwen.first_param_device(model)
    for i in range(0, len(prompts), bs):
        enc = tok(prompts[i:i + bs], return_tensors="pt", padding=True,
                  padding_side="left").to(dev)
        gen = model.generate(**enc, max_new_tokens=max_new, do_sample=False,
                             temperature=None, top_p=None, top_k=None,
                             pad_token_id=tok.pad_token_id or tok.eos_token_id)
        outs.extend(tok.batch_decode(gen[:, enc["input_ids"].shape[1]:],
                                     skip_special_tokens=True))
    return outs


# ------------------------------------------------------------------ main ----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=["baseline", "text", "embed"], required=True)
    ap.add_argument("--skill", default=os.path.join(ROOT, "skills", "spreadsheet_edit.md"))
    ap.add_argument("--vectors", default=None)
    ap.add_argument("--layers", default="34")
    ap.add_argument("--gamma", type=float, default=0.3)
    ap.add_argument("--mode", default="relative", choices=["relative", "raw"])
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--max-new-tokens", type=int, default=1536)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    if args.condition == "embed" and not args.vectors:
        ap.error("--condition embed requires --vectors")

    tasks = [t for t in json.load(open(os.path.join(DATA, "dataset.json")))
             if "exclude" not in t]
    pairs = []
    for t in tasks:
        init, golden = G.task_files(DATA, t)
        if init and golden:
            pairs.append((t, init, golden))
    pairs = pairs[:args.limit]
    i, k = (int(x) for x in args.shard.split("/"))
    pairs = pairs[i::k]
    print(f"[sb] {len(pairs)} tasks, shard {i}/{k}", flush=True)

    tok, model, layers = qwen.load(device_map="auto")
    system = open(args.skill).read() if args.condition == "text" else None
    prompts = [qwen.build_prompt(tok, build_question(t, init), system_msg=system)
               for t, init, _ in pairs]

    ctx, vec_meta = None, {}
    if args.condition == "embed":
        blob = torch.load(args.vectors, map_location="cpu")
        chosen = [int(x) for part in args.layers.split(",")
                  for x in ([part] if "-" not in part else
                            range(int(part.split("-")[0]), int(part.split("-")[1]) + 1))]
        vec_meta = {"file": os.path.basename(args.vectors), "pool": blob["meta"]["pool"],
                    "layers": chosen, "gamma": args.gamma, "mode": args.mode}
        ctx = hooks.inject(layers, {l: blob["vectors"][l] for l in chosen},
                           gamma=args.gamma, mode=args.mode)

    t0 = time.time()
    if ctx is not None:
        with ctx:
            replies = generate(tok, model, prompts, args.max_new_tokens, args.batch_size)
    else:
        replies = generate(tok, model, prompts, args.max_new_tokens, args.batch_size)
    dt = time.time() - t0

    records, n_code, n_ran = [], 0, 0
    for (t, init, golden), reply in zip(pairs, replies):
        code = extract_code(reply)
        n_code += code is not None
        produced, note = run_script(code, init)
        n_ran += produced is not None
        if produced:
            ok, ncell, mism, cnote = G.compare(produced, golden,
                                               t.get("answer_sheet"), t["answer_position"])
            os.remove(produced)
            note = cnote or (f"{mism}/{ncell} cells differ" if not ok else "")
        else:
            ok = False
        records.append({"id": t["id"], "gold": "golden",
                        "pred": note or "match", "em": float(ok), "f1": float(ok),
                        "instruction_type": t["instruction_type"], "raw": reply})

    n = len(records)
    em = sum(r["em"] for r in records) / n
    summary = {"domain": "spreadsheet", "condition": args.condition, "n": n,
               "model": qwen.MODEL_ID, "model_tag": qwen.model_tag(),
               "skill": os.path.basename(args.skill) if args.condition == "text" else None,
               "em": em, "f1": em, "seconds": round(dt, 1),
               "code_rate": n_code / n, "ran_rate": n_ran / n,
               "parse_rate": n_code / n, "forced": 0, "forced_rate": 0.0,
               "mean_pred_chars": sum(len(r["raw"]) for r in records) / n,
               "max_new_tokens": args.max_new_tokens,
               "vector": vec_meta, "shard": args.shard}

    name = args.tag or f"spreadsheet_{qwen.model_tag()}_{args.condition}"
    if args.condition == "text":
        name += "_" + os.path.basename(args.skill).replace(".md", "")
    if args.condition == "embed":
        name += "_" + vec_meta["file"].replace(".pt", "") + f"_L{args.layers}_g{args.gamma}"
    name += f"_s{i}of{k}"
    out = os.path.join(ROOT, "results", f"{name}.json")
    with open(out, "w") as f:
        json.dump({"summary": summary, "records": records}, f, indent=2)
    print(json.dumps(summary, indent=2), flush=True)
    print(f"[sb] wrote {out}", flush=True)


if __name__ == "__main__":
    main()
