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

1. **Constraint Verification First**: Before applying any formula or theorem, explicitly list every condition given in the problem (e.g., "convex", "integer sides", "exactly k", "adjacent"). If a standard method ignores a specific constraint, do not use it. Re-derive the solution from first principles that explicitly incorporate all constraints.

2. **Small-Case Validation**: For combinatorial counting, graph coloring, or sequence problems, always test your derived formula or logic on the smallest possible non-trivial case. If the formula fails the small case, it is incorrect. Do not assume or hallucinate known sequences; compute or prove them.

3. **Geometric & Structural Precision**: In geometry and graph problems, explicitly define the adjacency structure or offset region. Do not assume symmetry or vertex-transitivity unless rigorously proven. For offset/shrinking shapes, calculate the exact reduction in dimensions using trigonometric relations or vector projections, not heuristic guesses.

4. **Optimization Boundaries**: When maximizing or minimizing under bounds, rigorously check boundary conditions and integer constraints. Avoid assuming uniform or constant distributions. Use discrete case analysis or explicit enumeration of boundary configurations to find true extrema.

5. **Termination & Output Discipline**: Never enter infinite verification loops. Perform at most one rigorous sanity check (limit testing, dimensional analysis, or small-instance verification). Once verified, commit to a single, unambiguous answer and format it strictly as \boxed{answer}. If calculations diverge, backtrack to the core equation, correct arithmetic errors, and produce a final result.
<!-- SLOW_UPDATE_END -->
