# Research Mathematics: Exact Answers

## Setup
- Restate exactly what quantity is asked for, and under which hypotheses.

## Solving
- Choose a method that can actually produce that quantity; note which known result each step uses.

## Checking
- Test the answer against a special case, a limit, or a small instance before committing.

## Final Answer
- Give one closed-form answer in the requested form.

<!-- SLOW_UPDATE_START -->
When solving complex mathematical problems, strictly adhere to the following strategic directives:

1. **Literal Constraint & Negation Handling**: Read every condition exactly as written. If the problem states that symmetric configurations are "NOT considered equivalent," treat all positions as distinct and labeled. Do NOT apply Burnside's Lemma or divide by symmetry groups. If a constraint says "at most two parts" or "exactly one," model it precisely without assuming divisibility or uniform distribution.

2. **Theorem & Formula Verification on Base Cases**: Never apply a recalled theorem, sequence, or probability formula without verifying its domain and premises. Geometric probability formulas differ drastically between disks, boundaries, and hemispheres. Always test your recalled formula on $n=3$ or the smallest valid instance. If it contradicts manual enumeration, discard it and derive from first principles.

3. **Local vs. Global Condition Analysis**: Do not strengthen local logical conditions into global structural assumptions. A condition like "for every $u$, there exists a neighbor $v$ with no common neighbors" does NOT imply the graph is triangle-free. Analyze the exact logical scope and construct minimal counterexamples to test your assumptions.

4. **Construction Over Bounds**: For optimization, blocking, or covering problems, theoretical lower bounds (e.g., $\lceil 	ext{Total}/	ext{Capacity} ceil$) are necessary but not sufficient. You must explicitly construct a valid configuration to prove achievability. If your construction violates adjacency or boundary constraints, adjust your bound accordingly.

5. **Modular & Algebraic Precision**: When computing large powers modulo $M$, explicitly determine the cycle length (using Euler's theorem or direct tracking) before reducing exponents. Verify each multiplication step modulo $M$. Cross-check algebraic simplifications by substituting simple values back into the original expression.

6. **Mandatory Small-Instance Cross-Check**: Before committing to a final formula or answer, substitute $n=1, 2, 3$ into your derived expression. Manually compute the expected values for these cases. If your formula fails for any small instance, backtrack and correct the structural assumption immediately.
<!-- SLOW_UPDATE_END -->
