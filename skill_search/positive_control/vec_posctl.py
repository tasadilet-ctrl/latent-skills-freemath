"""Vector arm on the positive-control tasks (letter counting, long multiplication).

vec_mcq.py's design unchanged — B1 = skill − placebo, B2 = skill − nothing, CONTROL = placebo −
nothing; diff-in-means at the last prompt token; h += 0.3·‖h‖·v̂ at one fixed layer (8B L34,
14B L37); every cell on the same HF engine — with this module's tasks swapped in:

    train  40 items (seed 1), extraction pool only
    dev    16 items (seed 2), fidelity only
    test   150 items (seed 0), the pilot's items

    python vec_posctl.py extract|fidelity|eval|report --bench count|mult [...]   (vec_mcq.py's flags)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "vector_mcq"))
sys.path.insert(0, HERE)
import pilot  # noqa: E402
import vec_mcq as V  # noqa: E402

SUFFIX = "\n\nEnd your reply with a line of the form `Answer: <answer>`."
SEED = {"train": 1, "dev": 2, "test": 0}
NSPLIT = {"train": 40, "dev": 16, "test": 150}
TASK = None


def rows_for(bench, split):
    items = [it for it in pilot.gen(NSPLIT[split], seed=SEED[split]) if it[0] == bench]
    return [{"id": f"{bench}-{split}-{i}", "question": q, "answer": g, "options": []} for i, (t, q, g) in enumerate(items)]


V.rows_for = rows_for
V.render = lambda row: row["question"] + SUFFIX          # identical to pilot.py's prompt
V.parse = lambda pred, k: pilot.parse(pred, TASK)
V.ANSWER_CUE = "\n\nAnswer:"

if __name__ == "__main__":
    b = sys.argv[sys.argv.index("--bench") + 1] if "--bench" in sys.argv else None
    TASK = b
    if b:
        V.SKILL = os.path.join(HERE, "skills", f"{b}.md")
        V.PLACEBO = os.path.expanduser("~/mcq_math/skills/placebo_notation.md")
    sys.argv[0] = "vec_mcq.py"
    import runpy  # run vec_mcq's CLI with the patched module state
    ns = vars(V)
    ap_main = open(V.__file__).read().split('if __name__ == "__main__":', 1)[1]
    exec(compile("import argparse, os\n" + __import__("textwrap").dedent(ap_main), V.__file__, "exec"), ns)
