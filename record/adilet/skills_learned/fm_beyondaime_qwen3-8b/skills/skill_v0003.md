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

1. **Explicit Constraint Translation**: Convert every textual condition into a precise mathematical equation or inequality before proceeding. Do not assume standard interpretations; verify your model against the problem's simplest instance. If a constraint limits degrees of freedom, explicitly restrict your formulation accordingly.

2. **Theorem & Sequence Verification**: Never apply a known theorem, formula, or sequence value without explicitly verifying its prerequisites. Do not assume structural properties (e.g., bipartiteness, vertex-transitivity, independence polynomial values) without proof. If you recall a known result, derive it or validate it on a small case first. Hallucinated sequences or misapplied theorems are a primary failure mode.

3. **Rigorous Counting & Symmetry Handling**: When using combinatorial methods (Burnside's Lemma, recurrence relations, inclusion-exclusion), explicitly define the symmetry group, the set being acted upon, and the fixed-point conditions. Apply local constraints (e.g., adjacency, coloring rules) *before* reducing by symmetry. Always cross-check derived formulas by manually enumerating small cases ($n=1, 2, 3$).

4. **Extremal & Optimization Analysis**: Do not assume extrema occur at symmetric, uniform, or alternating configurations. Systematically test boundary cases, asymmetric distributions, and discrete breakpoints. For inequalities, verify the bound holds when variables approach 0 or dominate others, not just when they are equal. Use discrete case analysis to find true extrema.

5. **Calculation Discipline & Termination**: Avoid brute-force enumeration or step-by-step arithmetic for large parameters; derive structural patterns or use modular exponentiation rules correctly. Perform at most one rigorous sanity check (dimensional analysis, limit testing, or small-instance verification). Once verified, commit to a single answer. If calculations diverge or loop, immediately backtrack to the core mathematical model, correct the structural assumption, and resolve.
<!-- SLOW_UPDATE_END -->
