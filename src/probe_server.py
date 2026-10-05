"""Send real benchmark prompts to a hooked server and compare two runs."""
import argparse, json, sys, urllib.request, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def ask(port, msg, n=256):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=json.dumps({"model": "test", "messages": [{"role": "user", "content": msg}],
                         "max_tokens": n}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    m = d["choices"][0]["message"]
    return m.get("content") or ""

def prompts(k=5):
    sys.path.insert(0, ROOT)
    from src import evaluate
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "data/livemath.jsonl"))][:k]
    return [evaluate.render_question("livemath", r) for r in rows]

a = argparse.ArgumentParser()
a.add_argument("--port", type=int); a.add_argument("--out")
a.add_argument("--compare", nargs=2)
args = a.parse_args()

if args.compare:
    A = json.load(open(args.compare[0])); B = json.load(open(args.compare[1]))
    same = sum(1 for x, y in zip(A, B) if x == y)
    print(f"  identical outputs : {same}/{len(A)}")
    print(f"  differing outputs : {len(A)-same}/{len(A)}")
    for i, (x, y) in enumerate(zip(A, B)):
        if x != y:
            print(f"    first divergence at prompt {i}:")
            print(f"      plain : {x[:110]!r}")
            print(f"      steer : {y[:110]!r}")
            break
    print()
    print("  VERDICT:", "STEERING TAKES EFFECT through the server"
          if same < len(A) else
          "NO DIFFERENCE -- hooks are NOT biting through the server; do not run embed cells")
else:
    out = [ask(args.port, p) for p in prompts()]
    json.dump(out, open(args.out, "w"))
    print(f"  captured {len(out)} responses -> {os.path.basename(args.out)}")
