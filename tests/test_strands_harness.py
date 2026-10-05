"""Checks the Strands harness glue without needing a model endpoint.

Covers the three things that silently corrupt a run if they break:
workspace pinning (shards overwriting each other), the escape guard, and the
iteration cap (an uncapped agent burns the SLURM wall clock).
"""
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import strands_harness as S  # noqa: E402

FAIL = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(name)


def main():
    ws = tempfile.mkdtemp(prefix="strands-ws-")
    other = tempfile.mkdtemp(prefix="strands-other-")
    env = S.WorkspaceEnvironment(ws)

    print("workspace pinning")
    # shell runs in the workspace even though the process cwd is elsewhere
    os.chdir(other)
    res = asyncio.run(env.execute("pwd && echo marker > made_here.txt"))
    out = (getattr(res, "stdout", "") or "")
    check("shell cwd is the workspace", os.path.realpath(ws) in os.path.realpath(out.strip().splitlines()[0]) if out.strip() else False,
          f"got {out.strip().splitlines()[0] if out.strip() else '<empty>'}")
    check("file landed in workspace", os.path.exists(os.path.join(ws, "made_here.txt")))
    check("nothing landed in process cwd", not os.path.exists(os.path.join(other, "made_here.txt")))

    print("path resolution")
    check("relative path resolves under workspace",
          str(env._resolve_path("a/b.txt")).startswith(os.path.realpath(ws)))
    escaped = False
    try:
        env._resolve_path("../../../etc/passwd")
    except ValueError:
        escaped = True
    check("escape via .. is refused", escaped)
    escaped_abs = False
    try:
        env._resolve_path("/etc/passwd")
    except ValueError:
        escaped_abs = True
    check("escape via absolute path is refused", escaped_abs)

    print("symlinked sources (the OfficeQA case)")
    # OfficeQA symlinks each question's bulletins into the workspace. A
    # containment check using resolve() would follow the link out to the
    # shared docs dir and refuse every read.
    outside = os.path.join(other, "bulletin.txt")
    with open(outside, "w") as f:
        f.write("treasury")
    os.symlink(outside, os.path.join(ws, "bulletin.txt"))
    linked_ok = True
    try:
        env._resolve_path("bulletin.txt")
    except ValueError:
        linked_ok = False
    check("symlink inside the workspace is readable", linked_ok)
    check("and its content comes back",
          asyncio.run(env.read_file("bulletin.txt")) == b"treasury")

    print("file round-trip through the sandbox")
    asyncio.run(env.write_file("sub/x.txt", b"hello"))
    got = asyncio.run(env.read_file("sub/x.txt"))
    check("write_file/read_file round-trip", got == b"hello", repr(got))

    print("iteration cap")
    cap = S.IterationCap(3)
    raised = None
    try:
        for _ in range(10):
            cap._before_model(None)
    except S.EpisodeOver as e:
        raised = e.reason
    check("cap fires after the limit", raised == "iteration_cap" and cap.model_calls == 4,
          f"reason={raised} calls={cap.model_calls}")

    print("stuck detection")
    st = S.NoProgressStop(limit=3)
    fired = None
    try:
        for _ in range(5):
            st._after_tool(type("E", (), {"result": {"status": "error"}})())
    except S.EpisodeOver as e:
        fired = e.reason
    check("stops on consecutive errors", fired == "stuck")
    st2 = S.NoProgressStop(limit=3)
    for status in ("error", "error", "success", "error", "error"):
        st2._after_tool(type("E", (), {"result": {"status": status}})())
    check("a success resets the counter", st2.consecutive_errors == 2,
          f"got {st2.consecutive_errors}")

    print()
    print(f"{'ALL PASS' if not FAIL else 'FAILURES: ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
