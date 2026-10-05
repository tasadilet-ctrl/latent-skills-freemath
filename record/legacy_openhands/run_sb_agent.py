"""SpreadsheetBench through a real OpenHands agent, driven by the co-located qwen.

One Conversation per task. The agent gets a terminal and a file editor and a
workspace containing input.xlsx; it must leave output.xlsx behind. Grading is
the already-validated grade_spreadsheet.compare over the task's answer range.

Conditions:
  baseline   OpenHands' own system prompt, nothing added
  text       same, plus the skill appended via AgentContext.system_message_suffix

`system_message_suffix` APPENDS, so the agent's tool instructions are identical
in both arms and the skill is the only difference. The skill is deliberately NOT
registered as an OpenHands Skill: AgentSkills-format skills are advertised by
name and read on demand, so a null would mean "the agent never opened it"
rather than "the procedure did not help". A steering vector is applied
unconditionally, so its text counterpart must be too.

The embedding arm cannot run here -- litellm talks HTTP to vLLM, which exposes
no residual stream. It needs a hooked HF server behind the same API.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import grade_spreadsheet as G  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "spreadsheetbench_verified_400")

TASK_HINT = """The workbook `input.xlsx` is in your working directory.

{instruction}

The answer must end up in sheet {sheet}, range {rng}.

Produce `output.xlsx` by OPENING `input.xlsx` AND MODIFYING IT, then saving
under the new name. Do not build a new workbook from scratch: the grader looks
for the original sheet names, and a fresh openpyxl workbook is named 'Sheet',
so a correct answer in a new file still scores zero. Save with
openpyxl's `wb.save("output.xlsx")` so the result is a real .xlsx.

Put computed literal values in the answer cells, not formulas: nothing
recalculates formulas here, so a formula is stored without a value and reads
back as empty. When `output.xlsx` exists and is correct, you are done."""

# Official SpreadsheetBench does NOT give the model the answer position -- it is
# grading metadata. Supplying it made the 27B score 85.9% on the first 85 tasks,
# against ~50% published SOTA: near-ceiling, so a 2-point skill effect could not
# register. This variant withholds it, which both restores headroom and makes
# the numbers comparable to published work.
TASK_NOHINT = """The workbook `input.xlsx` is in your working directory.

{instruction}

Produce `output.xlsx` by OPENING `input.xlsx` AND MODIFYING IT, then saving
under the new name. Do not build a new workbook from scratch: the grader looks
for the original sheet names, and a fresh openpyxl workbook is named 'Sheet',
so a correct answer in a new file still scores zero. Save with
openpyxl's `wb.save("output.xlsx")` so the result is a real .xlsx.

Put computed literal values in the answer cells, not formulas: nothing
recalculates formulas here, so a formula is stored without a value and reads
back as empty. When `output.xlsx` exists and is correct, you are done."""


MAX_ROWS, MAX_COLS, MAX_CHARS = 60, 20, 6000


def render_workbook(path: str) -> str:
    """Inlined rather than imported from evaluate_spreadsheet.

    That module imports torch (for the hooks/steering path) and this script
    runs under the OpenHands venv, which has openpyxl but no torch.
    """
    import openpyxl
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception as e:
        return f"(could not read workbook: {type(e).__name__})"
    out, total = [], 0
    for ws in wb.worksheets:
        out.append(f"### Sheet {ws.title!r}  ({ws.max_row} rows x {ws.max_column} cols)")
        rows = []
        for r in range(1, min(ws.max_row, MAX_ROWS) + 1):
            cells = [("" if ws.cell(r, c).value is None else str(ws.cell(r, c).value)[:40])
                     for c in range(1, min(ws.max_column, MAX_COLS) + 1)]
            line = f"{r}: " + " | ".join(cells).rstrip(" |")
            rows.append(line); total += len(line)
            if total > MAX_CHARS:
                rows.append("... (truncated)"); break
        out.append("\n".join(rows))
        if ws.max_row > MAX_ROWS or ws.max_column > MAX_COLS:
            out.append(f"... (showing first {MAX_ROWS} rows x {MAX_COLS} cols)")
        if total > MAX_CHARS:
            out.append("... (remaining sheets omitted)"); break
    return "\n".join(out)


def render(task, init_path, hint=True):
    tpl = TASK_HINT if hint else TASK_NOHINT
    body = (tpl.format(instruction=task["instruction"].strip(),
                       sheet=task.get("answer_sheet") or "(the active sheet)",
                       rng=task["answer_position"])
            if hint else tpl.format(instruction=task["instruction"].strip()))
    return body + \
        "\n\nFor reference, here is what the workbook contains:\n" + \
        render_workbook(init_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=["baseline", "text"], required=True)
    ap.add_argument("--skill", default=os.path.join(ROOT, "skills", "spreadsheet_edit.md"))
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--max-iterations", type=int, default=15)
    ap.add_argument("--no-thinking", action="store_true",
                    help="Send chat_template_kwargs.enable_thinking=false. vLLM "
                         "runs --reasoning-parser qwen3, so a thinking model can "
                         "return reasoning with NO content and NO tool call; "
                         "OpenHands then burns a turn on corrective feedback. "
                         "Measured: 1.48 such turns/episode on Qwen3-8B vs 0.29 "
                         "on the 27B.")
    ap.add_argument("--stuck-detection", default="on", choices=["on", "off"],
                    help="OpenHands aborts loops it judges stuck; a weak model "
                         "retrying legitimately can trip it.")
    ap.add_argument("--location-hint", default="off", choices=["on", "off"],
                    help="'on' tells the model the answer sheet+range. Official "
                         "SpreadsheetBench does not; 'on' scored 85.9% vs ~50% "
                         "published, i.e. near-ceiling. Default off.")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    from openhands.sdk import LLM, Agent, AgentContext, Conversation, Tool
    # Tool names resolve through a global registry populated on import. Without
    # this the Agent ctor raises KeyError: ToolDefinition 'terminal' is not
    # registered -- which is what the first pilot hit, 20 tasks in 3 seconds.
    from openhands.tools.preset.default import register_default_tools
    register_default_tools(enable_browser=False)

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
    model = os.environ.get("LLM_MODEL", "anthropic/qwen3.6-27b")
    print(f"[sb-agent] {args.condition} via {base_url} model={model}", flush=True)

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
    print(f"[sb-agent] {len(pairs)} tasks, shard {i}/{k}", flush=True)

    skill_text = open(args.skill).read() if args.condition == "text" else None
    ctx = AgentContext(system_message_suffix=skill_text) if skill_text else None

    records, t0 = [], time.time()
    for n, (task, init, golden) in enumerate(pairs, 1):
        d = tempfile.mkdtemp(prefix="sbagent-")
        note, ok = "", False
        try:
            shutil.copy(init, os.path.join(d, "input.xlsx"))
            extra = ({"chat_template_kwargs": {"enable_thinking": False}}
                     if args.no_thinking else {})
            llm = LLM(model=model, base_url=base_url,
                      api_key=os.environ.get("LLM_API_KEY", "sk-anything"),
                      usage_id=f"sb-{task['id']}", timeout=1800, num_retries=3,
                      litellm_extra_body=extra)
            agent = Agent(llm=llm,
                          tools=[Tool(name="terminal"), Tool(name="file_editor")],
                          agent_context=ctx)
            conv = Conversation(agent=agent, workspace=d,
                                max_iteration_per_run=args.max_iterations,
                                stuck_detection=(args.stuck_detection == "on"),
                                visualizer=None, delete_on_close=True)
            conv.send_message(render(task, init, hint=(args.location_hint == "on")))
            conv.run()
            try:
                conv.close()
            except Exception:
                pass
            out = os.path.join(d, "output.xlsx")
            if not os.path.exists(out):
                note = "agent produced no output.xlsx"
            else:
                ok, ncell, mism, cnote = G.compare(
                    out, golden, task.get("answer_sheet"), task["answer_position"])
                note = cnote or (f"{mism}/{ncell} cells differ" if not ok else "")
        except Exception as e:
            note = f"{type(e).__name__}: {str(e)[:160]}"
        finally:
            shutil.rmtree(d, ignore_errors=True)
        records.append({"id": task["id"], "gold": "golden", "pred": note or "match",
                        "em": float(ok), "f1": float(ok),
                        "instruction_type": task["instruction_type"], "raw": note})
        if n % 5 == 0 or n == len(pairs):
            acc = sum(r["em"] for r in records) / len(records)
            print(f"[sb-agent] {n}/{len(pairs)}  acc={acc*100:.1f}%  "
                  f"({time.time()-t0:.0f}s)", flush=True)

    nn = len(records)
    em = sum(r["em"] for r in records) / nn
    tag = os.environ.get("MODEL_TAG", "qwen3.6-27b")
    summary = {"domain": "spreadsheet_agent",
               "condition": "embed" if steering else args.condition, "n": nn,
               "model": model, "model_tag": tag,
               "skill": os.path.basename(args.skill) if skill_text else None,
               "em": em, "f1": em, "seconds": round(time.time() - t0, 1),
               "parse_rate": 1.0, "forced": 0, "forced_rate": 0.0,
               "mean_pred_chars": 0.0, "max_new_tokens": 0,
               "max_iterations": args.max_iterations,
               "location_hint": args.location_hint,
               "no_thinking": args.no_thinking,
               "stuck_detection": args.stuck_detection,
               "vector": ({"file": steering.split()[0], "steering": steering,
                           "layers": [-1], "gamma": -1.0, "pool": "server",
                           "mode": "relative"} if steering else {}),
               "shard": args.shard}
    name = args.tag or f"spreadsheet_agent_{tag}_{args.condition}"
    if skill_text:
        name += "_" + os.path.basename(args.skill).replace(".md", "")
    name += f"_s{i}of{k}"
    out = os.path.join(ROOT, "results", f"{name}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump({"summary": summary, "records": records}, f, indent=2)
    print(json.dumps(summary, indent=2), flush=True)
    print(f"[sb-agent] wrote {out}", flush=True)


if __name__ == "__main__":
    main()
