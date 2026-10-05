"""OpenAI-compatible server backed by HF transformers WITH steering hooks.

Why this exists: the embedding arm needs `h_l += gamma * v` during generation.
vLLM exposes no access to the residual stream, and OpenHands reaches its model
over HTTP through litellm -- so there is no way to run the embed condition
through the agent harness against a vLLM server. This serves the same
`/v1/chat/completions` API from HF `transformers`, where forward hooks work,
so baseline / text / embed all run through ONE agent harness and differ only
in the thing under test.

    MODEL_ID=Qwen/Qwen3-14B python src/serve_hooked.py --port 8002
    MODEL_ID=Qwen/Qwen3-14B python src/serve_hooked.py --port 8002 \
        --vectors vectors/v_qwen3-14b_..._plain.pt --layers 30 --gamma 0.3

Tool calling: the chat template renders `tools`, and the model replies with
Hermes JSON inside <tool_call> tags (Qwen3 generation) or the qwen3_xml form
(Qwen3.6). Both are parsed back into OpenAI `tool_calls`, because a mismatch
here is silent -- vLLM's equivalent mismatch returned tool_calls=[] with the
call stranded in `content`, and the agent scored exactly 0 with no error.

Deliberately serial: one generation at a time under a lock. Steering hooks are
global to the model, so concurrent requests with different steering would
corrupt each other. Run client shards at low concurrency against this.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import uuid

import torch

# Imported at MODULE level on purpose. This file uses `from __future__ import
# annotations`, so FastAPI resolves the `request: Request` annotation from the
# module globals via get_type_hints. With the import inside build_app() the
# name is not there, FastAPI falls back to treating `request` as a QUERY
# parameter, and every POST returns 422 "Field required" -- with no server-side
# traceback, because it never reaches the handler.
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import hooks, qwen  # noqa: E402

_LOCK = threading.Lock()
STATE: dict = {}


# ------------------------------------------------------------ tool parsing --

_TC_BLOCK = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)
_XML_FN = re.compile(r"<function=([^>\s]+)\s*>(.*?)</function>", re.S)
_XML_PARAM = re.compile(r"<parameter=([^>\s]+)\s*>(.*?)</parameter>", re.S)


def parse_tool_calls(text: str):
    """Return (clean_text, [openai tool_call, ...]).

    Handles both generations' formats rather than assuming one:
      Qwen3    <tool_call>{"name": ..., "arguments": {...}}</tool_call>
      Qwen3.6  <tool_call><function=N><parameter=P>v</parameter></function>
    """
    calls = []
    for body in _TC_BLOCK.findall(text):
        name, args = None, {}
        body = body.strip()
        if body.startswith("{"):
            try:
                d = json.loads(body)
                name = d.get("name")
                args = d.get("arguments", d.get("parameters", {}))
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {"input": args}
            except Exception:
                continue
        else:
            m = _XML_FN.search(body)
            if m:
                name = m.group(1)
                args = {k: v.strip() for k, v in _XML_PARAM.findall(m.group(2))}
        if name:
            calls.append({
                "id": "call_" + uuid.uuid4().hex[:20],
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            })
    clean = _TC_BLOCK.sub("", text).strip()
    return clean, calls


def strip_thinking(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


# ------------------------------------------------------------ normalising --

def flatten_content(c):
    """OpenAI allows content to be a LIST of parts; Qwen's chat template assumes
    a string and does `content + "..."`, which raises
        TypeError: can only concatenate list (not "str") to list
    vLLM normalises this before templating; doing the same here.
    """
    if c is None:
        return ""
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        out = []
        for part in c:
            if isinstance(part, str):
                out.append(part)
            elif isinstance(part, dict):
                out.append(part.get("text") or part.get("content") or "")
        return "\n".join(x for x in out if x)
    return str(c)


def normalise_messages(msgs):
    """Make every message safe for a string-assuming chat template.

    Keeps tool_calls / tool_call_id intact -- the template needs them to render
    the agent's tool turns -- but forces `content` to a string everywhere.
    """
    out = []
    for m in msgs:
        n = dict(m)
        n["content"] = flatten_content(m.get("content"))
        if m.get("tool_calls"):
            n["tool_calls"] = m["tool_calls"]
        out.append(n)
    return out


# --------------------------------------------------------------- generation --

@torch.no_grad()
def generate(messages, tools, max_tokens, stop):
    tok, model, layers = STATE["tok"], STATE["model"], STATE["layers"]
    kw = {}
    if tools:
        kw["tools"] = [t["function"] if t.get("type") == "function" else t
                       for t in tools]
    try:
        prompt = tok.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=False, **kw)
    except TypeError:                      # template without enable_thinking
        prompt = tok.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, **kw)

    ids = tok(prompt, return_tensors="pt").to(qwen.first_param_device(model))
    ctx = STATE.get("ctx_factory")
    t0 = time.time()
    if ctx is not None:
        with ctx():
            out = model.generate(**ids, max_new_tokens=max_tokens,
                                 do_sample=False, temperature=None, top_p=None,
                                 top_k=None,
                                 pad_token_id=tok.pad_token_id or tok.eos_token_id)
    else:
        out = model.generate(**ids, max_new_tokens=max_tokens,
                             do_sample=False, temperature=None, top_p=None,
                             top_k=None,
                             pad_token_id=tok.pad_token_id or tok.eos_token_id)
    new = out[0, ids["input_ids"].shape[1]:]
    text = tok.decode(new, skip_special_tokens=True)
    for s in (stop or []):
        if s and s in text:
            text = text.split(s)[0]
    return text, int(new.shape[0]), int(ids["input_ids"].shape[1]), time.time() - t0


def build_app():
    app = FastAPI()

    @app.get("/v1/models")
    @app.get("/models")
    def models():
        return {"object": "list",
                "data": [{"id": STATE["served_name"], "object": "model",
                          "owned_by": "local"}]}

    @app.get("/health")
    def health():
        return {"status": "ok", "steering": STATE["steer_desc"]}

    # Both paths: litellm's openai provider appends /chat/completions to the
    # api_base, so whether the caller passes .../8079 or .../8079/v1 decides
    # which one is hit. Serving both removes a silent 404.
    @app.post("/v1/chat/completions")
    @app.post("/chat/completions")
    async def chat(request: Request):
        body = await request.json()
        msgs = body.get("messages", [])
        # Qwen's template wants at most one system message, first. An agent loop
        # routinely sends more; merge rather than 500 like the raw server does.
        msgs = normalise_messages(msgs)
        sysmsgs = [m for m in msgs if m.get("role") == "system"]
        rest = [m for m in msgs if m.get("role") != "system"]
        if len(sysmsgs) > 1:
            merged = "\n\n".join(str(m.get("content") or "") for m in sysmsgs)
            msgs = [{"role": "system", "content": merged}] + rest
        try:
            with _LOCK:                       # hooks are global; serialise
                text, ntok, nprompt, dt = generate(
                    msgs, body.get("tools"),
                    int(body.get("max_tokens") or 2048), body.get("stop"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JSONResponse(status_code=500,
                                content={"error": {"message": f"{type(e).__name__}: {e}"}})
        clean, calls = parse_tool_calls(strip_thinking(text))
        msg = {"role": "assistant", "content": clean or None}
        if calls:
            msg["tool_calls"] = calls
        return {
            "id": "chatcmpl-" + uuid.uuid4().hex[:16],
            "object": "chat.completion",
            "created": int(STATE["t0"] + dt),
            "model": STATE["served_name"],
            "choices": [{"index": 0, "message": msg,
                         "finish_reason": "tool_calls" if calls else "stop"}],
            "usage": {"prompt_tokens": nprompt, "completion_tokens": ntok,
                      "total_tokens": nprompt + ntok},
        }
    return app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8002)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--served-name", default=None)
    ap.add_argument("--vectors", default=None)
    ap.add_argument("--layers", default="")
    ap.add_argument("--gamma", type=float, default=0.3)
    ap.add_argument("--mode", default="relative", choices=["relative", "raw"])
    args = ap.parse_args()

    tok, model, layers = qwen.load(device_map="auto")
    STATE.update(tok=tok, model=model, layers=layers, t0=time.time(),
                 served_name=args.served_name or qwen.model_tag(),
                 steer_desc="none", ctx_factory=None)

    if args.vectors:
        blob = torch.load(args.vectors, map_location="cpu")
        chosen = []
        for part in args.layers.split(","):
            if "-" in part:
                a, b = part.split("-"); chosen += list(range(int(a), int(b) + 1))
            elif part:
                chosen.append(int(part))
        vecs = {l: blob["vectors"][l] for l in chosen}
        STATE["ctx_factory"] = lambda: hooks.inject(
            layers, vecs, gamma=args.gamma, mode=args.mode)
        STATE["steer_desc"] = (f"{os.path.basename(args.vectors)} "
                               f"L{args.layers} g{args.gamma} {args.mode}")
        print(f"[hooked] STEERING ON: {STATE['steer_desc']}", flush=True)
    else:
        print("[hooked] steering OFF (baseline/text arm)", flush=True)

    print(f"[hooked] serving {STATE['served_name']} on {args.host}:{args.port}",
          flush=True)
    import uvicorn
    uvicorn.run(build_app(), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
