"""Length-matched placebo: Adil's placebo_matched.md (neutral writing-style notes, no maths strategy) cut or
cycled line by line to the word count of a target skill.   python3 make_placebo.py <target skill.md> <out.md>"""
import os, re, sys
src = open(os.path.expanduser("~/for Adilet/skills/placebo_matched.md")).read().splitlines()
n = len(open(sys.argv[1]).read().split())
out, k, i = [], 0, 0
while k < n:
    w = src[i % len(src)].split(" ")
    take = w[: max(0, n - k)] if k + len(src[i % len(src)].split()) > n else w
    out.append(" ".join(take)); k += len(" ".join(take).split()); i += 1
while out and re.fullmatch(r"\s*(\d+\.)?\s*", out[-1]):
    out.pop()
open(sys.argv[2], "w").write("\n".join(out).rstrip() + "\n")
print(sys.argv[2], n, "words")
