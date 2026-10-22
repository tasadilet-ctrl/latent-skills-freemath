"""Free-form final-answer scoring for ArxivMath, RealMath and HARDMath2.

There are no options, so there is no answer-structure shortcut to learn. The
price is that equivalence has to be decided. Two checks, in order:

1. math-verify (symbolic), with float_rounding=10 so that a 6-digit decimal
   does not pass for an exact rational.
2. numeric: both right-hand sides are evaluated at random points of their free
   symbols. This is how HARDMath2 is graded, and it catches equivalent rewrites
   of asymptotic formulas that the symbolic check misses.

Only the final \\boxed{} answer (or <answer> tag) is scored, never the whole
reply, so an expression that merely appears in the working cannot score.

THREADS AND CRASHES. SkillOpt's rollout scores replies in a thread pool.
math-verify's own timeouts use signal.alarm(), which only works in the main
thread; in a worker it raises, and before this was fixed every symbolic and
numeric check silently returned "wrong" (only exact string matches counted).
Running sympy in many threads instead then segfaulted a training run. So the
symbolic and numeric checks now run in a separate process pool: a crash or hang
there costs one worker, the pool is rebuilt, and the check counts as "wrong".
In the main thread (offline rescoring) they run directly under signal.alarm.
"""
from __future__ import annotations

import multiprocessing as mp
import random
import re
import signal
import threading
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as _Timeout

_SYMBOL_ALIASES = [(r"\varepsilon", r"\epsilon"), (r"\dfrac", r"\frac"), (r"\tfrac", r"\frac"),
                   (r"\left", ""), (r"\right", ""), (r"\displaystyle", "")]
_DEADLINE_S = 20
_POOL: ProcessPoolExecutor | None = None
_POOL_LOCK = threading.Lock()


def _pool() -> ProcessPoolExecutor:
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            _POOL = ProcessPoolExecutor(max_workers=8, mp_context=mp.get_context("forkserver"))
        return _POOL


def _reset_pool(bad: ProcessPoolExecutor) -> None:
    """Drop a pool that crashed or holds a hung worker; the next call builds a fresh one."""
    global _POOL
    with _POOL_LOCK:
        if _POOL is not bad:
            return
        _POOL = None
    for proc in list(getattr(bad, "_processes", {}).values()):
        try:
            proc.kill()
        except Exception:
            pass
    bad.shutdown(wait=False, cancel_futures=True)


def _alarm(signum, frame):
    raise TimeoutError


def _with_deadline(fn, *args) -> bool:
    """fn(*args) under a deadline; False if it raises, crashes or overruns."""
    if threading.current_thread() is threading.main_thread():
        old = signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(_DEADLINE_S)
        try:
            return bool(fn(*args))
        except BaseException:
            return False
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    pool = _pool()
    try:
        return bool(pool.submit(fn, *args).result(timeout=_DEADLINE_S))
    except _Timeout:
        _reset_pool(pool)
        return False
    except Exception:        # BrokenProcessPool after a worker crash, or fn raising
        if getattr(pool, "_broken", False):
            _reset_pool(pool)
        return False


def _last_boxed(text: str) -> str | None:
    i = text.rfind("\\boxed{")
    if i < 0:
        return None
    j, depth = i + 7, 1
    while j < len(text) and depth:
        depth += (text[j] == "{") - (text[j] == "}")
        j += 1
    return text[i + 7:j - 1].strip() if depth == 0 else None


def extract_final(text: str) -> str | None:
    """The answer the reply committed to, or None."""
    b = _last_boxed(text or "")
    if b is not None:
        return b
    m = re.findall(r"<answer>(.*?)</answer>", text or "", re.DOTALL | re.IGNORECASE)
    if m:
        return m[-1].strip()
    return None


_DELIMS = [(r"\(", r"\)"), (r"\[", r"\]"), ("$$", "$$"), ("$", "$")]


def _clean(s: str) -> str:
    s = s.strip()
    inner = _last_boxed(s)
    if inner is not None:
        s = inner
    # strip math delimiters, repeatedly: RealMath writes \( 0 \), \[ ... \], $$ ... $$
    changed = True
    while changed:
        changed = False
        s = s.strip().rstrip(".,;").strip()
        for a, b in _DELIMS:
            if s.startswith(a) and s.endswith(b) and len(s) >= len(a) + len(b):
                s, changed = s[len(a):len(s) - len(b)], True
    for a, b in _SYMBOL_ALIASES:
        s = s.replace(a, b)
    return s.strip().rstrip(".,;").strip()


def _rhs(s: str) -> str:
    """'y(x) \\sim 2x + 1' -> '2x + 1'. Answers are often stated as equations."""
    parts = re.split(r"\\approx|\\sim|\\simeq|=", s)
    return parts[-1].strip() if parts and parts[-1].strip() else s


def _symbolic_raw(gold: str, pred: str) -> bool:
    from math_verify import parse, verify
    return bool(verify(parse(f"${gold}$", parsing_timeout=None), parse(f"${pred}$", parsing_timeout=None),
                       float_rounding=10, timeout_seconds=None))


def _symbolic(gold: str, pred: str) -> bool:
    return _with_deadline(_symbolic_raw, gold, pred)


def _to_sympy(s: str):
    from math_verify import parse
    out = parse(f"${s}$", parsing_timeout=None)
    for x in out:
        if hasattr(x, "free_symbols") and hasattr(x, "subs"):
            return x
    return None


def _numeric(gold: str, pred: str) -> bool:
    return _with_deadline(_numeric_raw, gold, pred)


def _numeric_raw(gold: str, pred: str, n: int = 6, rtol: float = 1e-6) -> bool:
    try:
        g, p = _to_sympy(_rhs(gold)), _to_sympy(_rhs(pred))
        if g is None or p is None:
            return False
        syms = sorted(g.free_symbols | p.free_symbols, key=str)
        # constants are the symbolic check's job: numerically, 0.428571 would pass for 3/7
        if not syms:
            return False
        # a prediction may not introduce symbols the gold answer does not have
        if p.free_symbols - g.free_symbols:
            return False
        rng = random.Random(0)
        agree = 0
        for _ in range(n):
            pt = {s: rng.uniform(0.3, 2.5) for s in syms}
            gv, pv = complex(g.evalf(subs=pt)), complex(p.evalf(subs=pt))
            if not all(map(lambda z: abs(z) < 1e12, (gv, pv))):
                continue
            if abs(gv - pv) > rtol * max(1.0, abs(gv)):
                return False
            agree += 1
        return agree >= 3
    except Exception:
        return False


def evaluate(prediction_text: str, ground_truth: str) -> dict:
    raw = extract_final(prediction_text)
    gold = _clean(ground_truth)
    if raw is None:
        return {"em": 0.0, "predicted_answer": "", "method": "no_final_answer"}
    pred = _clean(raw)
    if pred == gold:
        return {"em": 1.0, "predicted_answer": pred, "method": "string"}
    if _symbolic(gold, pred):
        return {"em": 1.0, "predicted_answer": pred, "method": "symbolic"}
    # answers are often stated as equations on one side only ("\omega = 1" vs "1"):
    # compare the right-hand sides, string first, then symbolically
    gr, pr = _rhs(gold), _rhs(pred)
    if (gr, pr) != (gold, pred) and gr and pr:
        if gr == pr:
            return {"em": 1.0, "predicted_answer": pred, "method": "rhs_string"}
        if _symbolic(gr, pr):
            return {"em": 1.0, "predicted_answer": pred, "method": "rhs_symbolic"}
    if _numeric(gold, pred):
        return {"em": 1.0, "predicted_answer": pred, "method": "numeric"}
    return {"em": 0.0, "predicted_answer": pred, "method": "mismatch"}
