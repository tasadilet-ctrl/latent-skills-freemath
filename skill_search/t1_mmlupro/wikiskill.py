"""WikiSkill (Tang et al., arXiv 2608.27454, Algorithm 1 + Appendix C/E) for k-option MCQ maths, on our servers.

    python wikiskill.py --split-dir ~/skillopt_work/mq_split/mmlupro_math_tq_sb --out <workspace> \
        --target-url http://localhost:P1/v1 --target-model Qwen/Qwen3-4B \
        --opt-url http://localhost:P2/v1 --opt-model Qwen/Qwen3.6-27B --seed 1 [--iters 8 --max-tokens 2048]

Loop (paper's Algorithm 1): S0 = {} and W0 = {}; baseline validation sets R_best; for k = 1..K (stop when R_best = 1):
roll out the answering model on all training tasks with the active skills in its system prompt (no wiki access)
-> raw/traces/iter<k>/; the Wiki Maintainer (one call) consolidates a stratified sample (<= 5 failing + <= 3 passing
traces, 15,000 chars each) into wiki/patterns/, wiki/index.md, wiki/log.md; the Skill Proposer (ReAct, tools
read_file / finish, must read >= 4 traces before a create/patch) proposes one atomic change; the candidate skill set is
scored on validation and kept only if strictly better (else the skills roll back, the wiki stays); the harness appends
the proposal, its diff, the score and Accepted/Rejected to wiki/skill-impact.md.
Maintainer and proposer system prompts are the paper's (E.2, E.3) verbatim; the proposer's {task_desc} is ours, and
the tool-call syntax (<tool_call>{json}</tool_call>, Qwen's native format) is the one thing the paper leaves open.
Answering = the kit's MCQ prompt, parser and answer forcing (evaluate_vllm_mcq.py, as evaluate_mcq_t1.py and the
SkillOpt mcqkit env), thinking off, the skill section as system prompt (none when there are no skills).
Outputs: <out>/best_skill.md (the final skill section, = what is tested), summary.json, history.jsonl, and the
workspace (raw/, wiki/, skills/).
"""
from __future__ import annotations

import argparse
import asyncio
import difflib
import json
import os
import random
import re
import shutil
import sys
import time

from openai import AsyncOpenAI

sys.path.insert(0, os.path.expanduser("~/mcq_math"))
from evaluate_vllm_mcq import ANSWER_CUE, parse, render  # noqa: E402

TRACE_CAP = 15000
MAX_FAIL, MAX_PASS = 5, 3
PROPOSER_TURNS = 30
PROPOSER_CHAR_BUDGET = 300_000  # ~ 85k tokens of tool output, then the proposer is told to finish

WIKI_MAINTAINER_PROMPT = """You are a Wiki Maintainer Agent for an LLM skill evolution system.

Your job is to maintain a structured knowledge base (wiki) that documents patterns observed during agent execution -- both successes and failures. You must perform DEEP ANALYSIS of execution logs to identify root causes, not just surface-level symptoms.

## Wiki Structure
The wiki is organized as:
- wiki/index.md -- Concise catalog of known patterns (one line per pattern)
- wiki/log.md -- Chronological evolution log (iterations, scores, accept/reject)
- wiki/skill-impact.md -- Record of which skills were tried and their outcomes
- wiki/patterns/ -- One page per pattern with detailed evidence and analysis

## Your Input
1. Execution traces from the latest iteration -- including full agent execution logs showing what actions the agent took, what commands it ran, and what environment feedback it observed
2. The current wiki context (index, log, pattern pages)

## Your Output (Incremental Edit Mode)
Return a JSON object with these keys:
- "create_patterns": list of {"name": "pattern-name.md", "content": "..."} -- new patterns (full content)
- "update_patterns": list of {"name": "existing-pattern.md", "edits": [...]} -- patch existing patterns
- "update_index": full updated content of index.md (always provide the complete index)
- "append_log": "brief summary of this iteration's findings and actions"

"update_index" and "append_log" are REQUIRED. Always provide them, even if there are no new patterns. For "update_index", always provide the complete updated index content including all existing entries plus any new ones.

### Patch Operations (for update_patterns only)
For "update_patterns", each entry uses an "edits" list of patch operations:
- {"op": "append", "content": "text to add at end"}
- {"op": "replace", "target": "exact text to find", "content": "replacement text"}
- {"op": "insert_after", "target": "exact text to find", "content": "text to insert after"}

Rules for patch operations:
1. "target" must be an EXACT substring of the existing content.
2. Use "append" to add new evidence. Use "replace" to fix or refine existing text.
3. Use "insert_after" to add entries after a specific line.
4. Keep each edit minimal -- only change what's needed.
5. For NEW patterns (create_patterns), use full "content".

## Analysis Guidelines

### Deep Trace Analysis (CRITICAL)
When execution logs are provided, you MUST:
1. Read the agent's actual actions -- what commands did it issue?
2. Compare successful vs failed tasks -- what did successful tasks do differently?
3. Identify ACTION PATTERNS and strategies, not just error messages.
4. Check whether the agent followed any active skills, and whether the skill guidance was helpful or not

### Pattern Documentation Rules
1. Each pattern page should document:
   - What the pattern is (description)
   - Root cause analysis (WHY it happens, not just WHAT happens)
   - Exact command sequences from traces (what the agent did wrong / right)
   - Known solutions or workarounds (concrete action patterns with exact syntax)
2. Capture BOTH success and failure patterns:
   - **Failure patterns**: Document what went wrong and how to avoid it
   - **Success patterns**: Document strategies that consistently lead to task completion
3. Do NOT create duplicate patterns -- update existing ones with new evidence
4. Be concise. Pattern pages should be 10-30 lines, not essays.
5. Only create patterns for meaningful, generalizable observations.

### Index Description Quality (CRITICAL)
The index.md entries are the MOST IMPORTANT part of the wiki because they determine whether inference agents will read the full pattern pages.

Each index entry MUST follow this format:
- [pattern-name](wiki/patterns/pattern-name.md): PROBLEM + ROOT CAUSE + FIX in one or two sentence.

The description must be specific enough that an agent can judge relevance without reading the full page. Include the problem, root cause, AND solution."""

SKILL_PROPOSER_PROMPT = """You are a Skill Proposer Agent for an LLM agent that solves {task_desc}.
Your job is to explore the wiki knowledge base and execution traces, diagnose root causes of failures, and propose a skill change (create or patch).

## Tools Available
You have two tools:
1. `read_file(path)` -- Read a wiki file or execution log. Paths are relative to the workspace root.
2. `finish(proposal)` -- Submit your final skill proposal as a JSON object.

## Workflow
1. Start by reading `wiki/index.md` to understand what patterns exist
2. Read `wiki/skill-impact.md` to see what was tried before (includes full content of rejected proposals -- DO NOT repeat rejected approaches)
3. Read specific pattern pages that seem relevant to the current failures
4. Read execution traces for failed tasks via `traces/<task_id>` to understand root causes
5. Decide: create (new skill) or patch (edit existing skill), or no_action
6. If proposing a change, call `finish` with the full proposal

## finish() Proposal Format
For creating a new skill:
- "action": "create"
- "name": skill directory name (snake_case)
- "skill_md": full SKILL.md content with YAML frontmatter + When to Apply + When NOT to Apply + Instructions
- "purpose_md": full PURPOSE.md content with Origin + Patterns Addressed + Evolution History

For patching an existing skill:
- "action": "patch"
- "name": existing skill directory name
- "edits": list of patch operations:
  - {{"op": "append", "content": "text to add at end"}}
  - {{"op": "replace", "target": "exact text to find", "content": "replacement"}}
  - {{"op": "insert_after", "target": "exact text to find", "content": "text to insert after"}}
  Each "replace" target should be a short, specific section -- not the entire file. If you need to change most of the file, use "action": "create" instead.

If no action is needed, call finish with: {{"action": "no_action"}}

## Rules
1. Read the wiki FIRST -- don't propose something that was already tried and rejected. skill-impact.md contains full content of rejected proposals.
2. Focus on action patterns and concrete strategies.
3. Keep skills concise and actionable.
4. You MUST read at least 4 execution traces before proposing a skill change. Target your exploration based on the trace summary.
5. Prefer patching existing skills over creating new ones when the existing skill is partially correct."""

# Ours: how to call the tools (the paper does not print its tool-call syntax).
TOOL_SYNTAX = """

## How to call a tool
End every message with exactly one tool call in this form (JSON inside the tags):
<tool_call>{"name": "read_file", "arguments": {"path": "wiki/index.md"}}</tool_call>
<tool_call>{"name": "finish", "arguments": {"proposal": {"action": "no_action"}}}</tool_call>
You will receive the tool result in the next message."""

TASK_DESC = "multiple-choice mathematics questions (MMLU-Pro math, 10 options, answer given as a single letter)"


# ---------------------------------------------------------------- data and answering
def load_split(d):
    rows = []
    for it in json.load(open(d)):
        rows.append({"id": str(it["id"]), "question": it["question"], "options": [c["text"] for c in it["choices"]],
                     "answer": it["correct_choice"]["label"]})
    return rows


def safe_id(i):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", i)


class Answerer:
    def __init__(self, url, model, max_tokens, conc):
        self.cli = AsyncOpenAI(base_url=url, api_key="x", timeout=3600)
        self.model, self.max_tokens, self.sem = model, max_tokens, asyncio.Semaphore(conc)

    async def one(self, row, system, seed):
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": render(row)}]
        async with self.sem:
            r = await self.cli.chat.completions.create(
                model=self.model, messages=msgs, temperature=1.0, top_p=1.0, max_tokens=self.max_tokens,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}, "seed": seed})
            out = r.choices[0].message.content or ""
            forced = False
            if parse(out, len(row["options"])) is None:  # the kit's forcing: append the answer cue, 12 tokens
                r2 = await self.cli.chat.completions.create(
                    model=self.model, messages=msgs + [{"role": "assistant", "content": out + ANSWER_CUE}],
                    temperature=1.0, top_p=1.0, max_tokens=12,
                    extra_body={"chat_template_kwargs": {"enable_thinking": False}, "seed": seed,
                                "continue_final_message": True, "add_generation_prompt": False})
                out, forced = out + ANSWER_CUE + (r2.choices[0].message.content or ""), True
        p = parse(out, len(row["options"]))
        return {"id": row["id"], "pred": p, "gold": row["answer"], "em": float(p == row["answer"]), "forced": forced,
                "reply": out, "question": render(row)}

    async def run(self, rows, system, base_seed, repeats=1):
        jobs = [self.one(r, system, base_seed + 10 * i + k) for i, r in enumerate(rows) for k in range(repeats)]
        return await asyncio.gather(*jobs)


# ---------------------------------------------------------------- workspace helpers
def read(p, default=""):
    return open(p).read() if os.path.exists(p) else default


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(s)


def apply_edits(text, edits):
    """Paper's patch ops. Returns (new text, list of failed ops)."""
    bad = []
    for e in edits or []:
        op, c, t = e.get("op"), e.get("content", ""), e.get("target")
        if op == "append":
            text = text.rstrip("\n") + "\n" + c + ("\n" if not c.endswith("\n") else "")
        elif op in ("replace", "insert_after") and t and t in text:
            text = text.replace(t, c, 1) if op == "replace" else text.replace(t, t + "\n" + c, 1)
        else:
            bad.append(e)
    return text, bad


def skill_names(ws):
    d = os.path.join(ws, "skills")
    return sorted(n for n in os.listdir(d) if os.path.isfile(os.path.join(d, n, "SKILL.md"))) if os.path.isdir(d) else []


def skill_section(ws):
    """The {skill_section}: every active SKILL.md, full injection (paper 3.2.1). Empty set -> no system prompt."""
    parts = [read(os.path.join(ws, "skills", n, "SKILL.md")).strip() for n in skill_names(ws)]
    return "\n\n---\n\n".join(p for p in parts if p) or None


def extract_json(s):
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s.strip())
    i, j = s.find("{"), s.rfind("}")
    return json.loads(s[i:j + 1])


def trace_text(rec, names):
    return (f"# Task {rec['id']}\nActive skills: {', '.join(names) or '(none)'}\n\n## Question\n{rec['question']}\n\n"
            f"## Agent reply\n{rec['reply']}\n\n## Result\npredicted: {rec['pred']}  gold: {rec['gold']}  "
            f"{'CORRECT' if rec['em'] else 'WRONG'}{'  (answer forced: no committed letter)' if rec['forced'] else ''}\n")[:TRACE_CAP]


# ---------------------------------------------------------------- optimizer agents
class Optimizer:
    def __init__(self, url, model):
        self.cli = AsyncOpenAI(base_url=url, api_key="x", timeout=3600)
        self.model = model

    async def chat(self, msgs, max_tokens=32768):
        r = await self.cli.chat.completions.create(
            model=self.model, messages=msgs, temperature=1.0, top_p=1.0, max_tokens=max_tokens,
            extra_body={"chat_template_kwargs": {"enable_thinking": True}})
        return r.choices[0].message.content or ""


async def maintain_wiki(opt, ws, k, sample, log):
    W = os.path.join(ws, "wiki")
    pages = sorted(os.listdir(os.path.join(W, "patterns"))) if os.path.isdir(os.path.join(W, "patterns")) else []
    ctx = (f"## Current wiki\n### wiki/index.md\n{read(W + '/index.md', '(empty)')}\n\n### wiki/log.md\n"
           f"{read(W + '/log.md', '(empty)')}\n\n### wiki/patterns/\n" +
           ("\n\n".join(f"#### wiki/patterns/{p}\n{read(os.path.join(W, 'patterns', p))}" for p in pages) or "(none)"))
    tr = "\n\n".join(t for _, t in sample)
    msgs = [{"role": "system", "content": WIKI_MAINTAINER_PROMPT},
            {"role": "user", "content": f"{ctx}\n\n## Execution traces (iteration {k}, {len(sample)} sampled)\n\n{tr}\n\n"
                                        "Return the JSON object now."}]
    for attempt in range(3):
        out = await opt.chat(msgs)
        try:
            j = extract_json(out)
            break
        except Exception as e:  # noqa: BLE001
            log(f"  [maintainer] JSON parse failed ({e}); retry {attempt + 1}")
            msgs += [{"role": "assistant", "content": out[-4000:]},
                     {"role": "user", "content": "That was not a valid JSON object. Return only the JSON object."}]
    else:
        log("  [maintainer] no valid JSON; wiki unchanged this iteration")
        return {"created": 0, "updated": 0, "failed_edits": 0, "ok": False}
    nc = nu = nbad = 0
    for p in j.get("create_patterns") or []:
        name = safe_id(os.path.basename(p.get("name", ""))) or f"pattern-{k}-{nc}.md"
        name = name if name.endswith(".md") else name + ".md"
        write(os.path.join(W, "patterns", name), p.get("content", ""))
        nc += 1
    for p in j.get("update_patterns") or []:
        f = os.path.join(W, "patterns", safe_id(os.path.basename(p.get("name", ""))))
        if not os.path.exists(f):
            nbad += 1
            continue
        txt, bad = apply_edits(read(f), p.get("edits"))
        write(f, txt)
        nu += 1
        nbad += len(bad)
    if j.get("update_index"):
        write(W + "/index.md", j["update_index"])
    write(W + "/log.md", read(W + "/log.md") + f"\n## Iteration {k}\n{j.get('append_log', '')}\n")
    return {"created": nc, "updated": nu, "failed_edits": nbad, "ok": True}


TOOL_RE = re.compile(r"<tool_call>\s*(\{.*\})\s*</tool_call>", re.S)


async def propose(opt, ws, k, train_recs, log):
    names = skill_names(ws)
    summary = "\n".join(f"- {r['id']}: {'PASS' if r['em'] else 'FAIL'} (predicted {r['pred']}, gold {r['gold']})"
                        for r in train_recs)
    cur = "\n\n".join(f"### skills/{n}/SKILL.md\n{read(os.path.join(ws, 'skills', n, 'SKILL.md'))}" for n in names)
    user = (f"Iteration {k}.\n\n## wiki/index.md\n{read(ws + '/wiki/index.md', '(empty)')}\n\n## wiki/skill-impact.md\n"
            f"{read(ws + '/wiki/skill-impact.md', '(no proposals yet)')}\n\n## Current skills\n{cur or '(none: the skill set is empty)'}"
            f"\n\n## Training outcomes (this iteration, {sum(r['em'] for r in train_recs):.0f}/{len(train_recs)} correct)\n"
            f"{summary}\n\nTraces are at traces/<task_id>. Begin.")
    msgs = [{"role": "system", "content": SKILL_PROPOSER_PROMPT.format(task_desc=TASK_DESC) + TOOL_SYNTAX},
            {"role": "user", "content": user}]
    traces_read, chars, turns = set(), 0, 0
    tdir = os.path.join(ws, "raw", "traces", f"iter{k}")
    while turns < PROPOSER_TURNS + 2:
        turns += 1
        out = await opt.chat(msgs, max_tokens=16384)
        msgs.append({"role": "assistant", "content": out})
        m = TOOL_RE.findall(out)
        if not m:
            msgs.append({"role": "user", "content": "No tool call found. End your message with one <tool_call>{...}</tool_call>."})
            continue
        try:
            call = json.loads(m[-1])
            name, args = call.get("name"), call.get("arguments") or {}
        except Exception as e:  # noqa: BLE001
            msgs.append({"role": "user", "content": f"Could not parse the tool call JSON ({e}). Try again."})
            continue
        if name == "read_file":
            path = str(args.get("path", "")).lstrip("/")
            if path.startswith("traces/"):
                f = os.path.join(tdir, safe_id(path[len("traces/"):].removesuffix(".md")) + ".md")
            else:
                f = os.path.normpath(os.path.join(ws, path))
            if not f.startswith(os.path.abspath(ws)) or not os.path.isfile(f):
                res = f"Error: {path} does not exist."
            else:
                res = read(f)[:TRACE_CAP]
                if path.startswith("traces/"):
                    traces_read.add(f)
            chars += len(res)
            note = "" if chars < PROPOSER_CHAR_BUDGET else "\n\n[Context budget reached: call finish now.]"
            if turns >= PROPOSER_TURNS:
                note += "\n\n[Turn limit reached: call finish now.]"
            msgs.append({"role": "user", "content": f"<tool_response>\n{res}\n</tool_response>{note}"})
        elif name == "finish":
            prop = args.get("proposal", args)
            if isinstance(prop, str):
                try:
                    prop = json.loads(prop)
                except Exception:  # noqa: BLE001
                    prop = {}
            act = prop.get("action")
            if act in ("create", "patch") and len(traces_read) < 4 and turns < PROPOSER_TURNS:
                msgs.append({"role": "user", "content": f"Rejected: you have read {len(traces_read)} execution traces; "
                             "you MUST read at least 4 before proposing a skill change."})
                continue
            if act not in ("create", "patch", "no_action"):
                msgs.append({"role": "user", "content": "Invalid proposal: action must be create, patch or no_action."})
                continue
            log(f"  [proposer] {act} {prop.get('name', '')} after {turns} turns, {len(traces_read)} traces read")
            return prop, turns, len(traces_read)
        else:
            msgs.append({"role": "user", "content": f"Unknown tool {name}. Use read_file or finish."})
    log("  [proposer] no proposal within the turn limit -> no_action")
    return {"action": "no_action"}, turns, len(traces_read)


def apply_proposal(ws, prop, k):
    """Returns (ok, message, target name). Writes into ws/skills."""
    act, name = prop.get("action"), safe_id(str(prop.get("name", "")).strip()) or f"skill_{k}"
    d = os.path.join(ws, "skills", name)
    if act == "create":
        if not prop.get("skill_md"):
            return False, "create without skill_md", name
        write(os.path.join(d, "SKILL.md"), prop["skill_md"])
        write(os.path.join(d, "PURPOSE.md"), prop.get("purpose_md", ""))
        return True, "created", name
    if act == "patch":
        f = os.path.join(d, "SKILL.md")
        if not os.path.exists(f):
            return False, f"patch of unknown skill {name}", name
        txt, bad = apply_edits(read(f), prop.get("edits"))
        if bad and txt == read(f):
            return False, f"no patch op applied ({len(bad)} targets not found)", name
        write(f, txt)
        return True, f"patched ({len(bad)} ops not applied)" if bad else "patched", name
    return False, "no_action", name


def snapshot(ws):
    return {n: {f: read(os.path.join(ws, "skills", n, f)) for f in ("SKILL.md", "PURPOSE.md")} for n in skill_names(ws)}


def restore(ws, snap):
    shutil.rmtree(os.path.join(ws, "skills"), ignore_errors=True)
    os.makedirs(os.path.join(ws, "skills"), exist_ok=True)
    for n, fs in snap.items():
        for f, s in fs.items():
            write(os.path.join(ws, "skills", n, f), s)


def flat(snap):
    return "".join(f"=== skills/{n}/SKILL.md\n{fs['SKILL.md']}\n" for n, fs in sorted(snap.items()))


# ---------------------------------------------------------------- main loop
async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--target-url", required=True)
    ap.add_argument("--target-model", required=True)
    ap.add_argument("--opt-url", required=True)
    ap.add_argument("--opt-model", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--iters", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--val-repeats", type=int, default=1)
    ap.add_argument("--conc", type=int, default=128)
    a = ap.parse_args()
    ws = os.path.abspath(a.out)
    for d in ("raw/traces", "wiki/patterns", "skills"):
        os.makedirs(os.path.join(ws, d), exist_ok=True)
    logf = open(os.path.join(ws, "wikiskill.log"), "a")

    def log(s):
        line = f"{time.strftime('%F %T')} {s}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()

    train = load_split(os.path.join(a.split_dir, "train", "items.json"))
    val = load_split(os.path.join(a.split_dir, "val", "items.json"))
    ans = Answerer(a.target_url, a.target_model, a.max_tokens, a.conc)
    opt = Optimizer(a.opt_url, a.opt_model)
    rnd = random.Random(a.seed)
    hist = open(os.path.join(ws, "history.jsonl"), "a")
    log(f"[wikiskill] target={a.target_model} opt={a.opt_model} seed={a.seed} K={a.iters} train={len(train)} val={len(val)}x{a.val_repeats}")

    async def score_val(k):
        recs = await ans.run(val, skill_section(ws), a.seed * 1_000_003 + 500_000 + k * 7919, a.val_repeats)
        return sum(r["em"] for r in recs) / len(recs)

    t0 = time.time()
    best = await score_val(0)
    base = best
    log(f"[baseline] val={best:.4f} (empty skill set)")
    accepts = 0
    for k in range(1, a.iters + 1):
        if best >= 1.0:
            log("[stop] R_best = 1.0")
            break
        tk = time.time()
        names = skill_names(ws)
        recs = await ans.run(train, skill_section(ws), a.seed * 1_000_003 + k * 7919)
        tdir = os.path.join(ws, "raw", "traces", f"iter{k}")
        for r in recs:
            write(os.path.join(tdir, safe_id(r["id"]) + ".md"), trace_text(r, names))
        tr_acc = sum(r["em"] for r in recs) / len(recs)
        fails = [r for r in recs if not r["em"]]
        passes = [r for r in recs if r["em"]]
        sample = rnd.sample(fails, min(MAX_FAIL, len(fails))) + rnd.sample(passes, min(MAX_PASS, len(passes)))
        log(f"[iter {k}] train={tr_acc:.3f} skills={names} sample={len(sample)}")
        wm = await maintain_wiki(opt, ws, k, [(r["id"], trace_text(r, names)) for r in sample], log)
        log(f"  [maintainer] {wm}")
        before = snapshot(ws)
        prop, turns, nread = await propose(opt, ws, k, recs, log)
        ok, msg, target = apply_proposal(ws, prop, k)
        cand = snapshot(ws) if ok else before
        diff = "".join(difflib.unified_diff(flat(before).splitlines(True), flat(cand).splitlines(True),
                                            "skills_before", "skills_candidate"))
        prev, score, decision = best, None, "Rejected"
        if ok:
            score = await score_val(k)
            if score > best:
                decision, best = "Accepted", score
                accepts += 1
            else:
                restore(ws, before)
        head = f"\n## Iteration {k}: {prop.get('action')} `{target}` -> {decision.upper()}"
        if score is not None:
            head += f" (val {score:.4f} vs best {prev:.4f})"
        else:
            head += f" (not evaluated: {msg})"
        write(ws + "/wiki/skill-impact.md", read(ws + "/wiki/skill-impact.md", "# Skill impact\n")
              + head + "\n```diff\n" + diff[:20000] + "\n```\n")
        rec = {"iter": k, "train_acc": tr_acc, "maintainer": wm, "action": prop.get("action"), "target": target,
               "apply": msg, "val": score, "decision": decision, "best": best, "proposer_turns": turns,
               "traces_read": nread, "skills_after": skill_names(ws), "sec": round(time.time() - tk, 1)}
        hist.write(json.dumps(rec) + "\n")
        hist.flush()
        log(f"[iter {k}] {prop.get('action')} {target}: {msg}; val={score} -> {decision}; best={best:.4f} ({rec['sec']}s)")
    final = skill_section(ws) or ""
    write(os.path.join(ws, "best_skill.md"), final + ("\n" if final else ""))
    json.dump({"method": "wikiskill", "target": a.target_model, "optimizer": a.opt_model, "seed": a.seed,
               "iters": a.iters, "baseline_val": base, "best_val": best, "accepts": accepts,
               "skills": skill_names(ws), "words": len(final.split()), "wall_s": round(time.time() - t0, 1)},
              open(os.path.join(ws, "summary.json"), "w"), indent=1)
    log(f"[done] val {base:.4f} -> {best:.4f}, accepts={accepts}, skills={skill_names(ws)}")


if __name__ == "__main__":
    asyncio.run(main())
