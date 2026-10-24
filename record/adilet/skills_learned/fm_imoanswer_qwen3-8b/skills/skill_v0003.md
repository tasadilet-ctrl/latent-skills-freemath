# Research Mathematics: Exact Answers

## Setup
- Restate exactly what quantity is asked for, and under which hypotheses.

## Solving

- Compute initial terms or evaluate specific configurations (symmetric, boundary, degenerate) to establish bounds or identify patterns before generalizing.
- When solving polynomial identities, explicitly equate degrees and leading coefficients to isolate constants or determine parameter constraints.

- Explicitly map given conditions to a concrete mathematical framework (e.g., coordinate geometry, combinatorial counting, or known theorems) before deriving.
- Use double-counting or invariant arguments to translate combinatorial/geometric constraints into algebraic equations or inequalities.
- Structure the solution into clearly labeled steps, explicitly stating which mathematical principle or identity justifies each transition.
- Derive the result step-by-step using rigorous algebraic, combinatorial, or geometric methods. Explicitly track how variables are coupled and incorporate all constraints (e.g., index gaps, modular restrictions, parity).
- Do not guess constants, invoke vague "known results", or assume extreme symmetry/degenerate cases without explicit proof. Justify each transformation and evaluate intermediate sums, counts, or bounds concretely.

## Checking
- Integrate constraints *during* derivation, not just at the end. Explicitly solve inequalities/equations to find feasible ranges. Verify that every intermediate configuration (geometric, modular, combinatorial) strictly satisfies all given bounds and conditions before proceeding.
- Test the derived formula against trivial cases, limits, and small instances ($n=1,2,3$) to catch off-by-one errors or missing factors. Validate algebraic consistency, dimensional analysis, and scaling behavior.
- Reject numerical approximations; ensure all expressions are exact and fully simplified before committing.

## Final Answer
- Give one closed-form answer in the requested form.

<!-- SLOW_UPDATE_START -->
Geometric Precision: Map every named point to its exact definition before computing lengths or angles. When calculating a segment (e.g., $ZQ$), verify both endpoints and the line it lies on. Never conflate a foot of an altitude with a vertex, or a segment length with a perpendicular distance. Use coordinates or vectors to prove any claimed parallelism, perpendicularity, or symmetry.

Constraint-Driven Derivation: Integrate all problem constraints (bounds, parity, modular conditions, domain restrictions) at every algebraic step, not just at the end. If an intermediate result violates a constraint, backtrack immediately. For inequalities, verify the direction of each step and test boundary cases explicitly.

Combinatorial & Sequence Rigor: Explicitly compute the first 3-4 terms or configurations to establish patterns. Validate any proposed recurrence or formula against these concrete cases before generalizing. Do not guess constants or invoke vague "known results." Derive counting arguments from first principles, small cases, or generating functions.

Symmetry & Assumption Ban: Do not assume symmetry, regularity, or special configurations unless explicitly stated or rigorously derived. Stress-test your candidate solution with asymmetric or degenerate cases. If a geometric or algebraic property isn't proven, discard it.

Anti-Looping & Output Control: If your reasoning repeats the same step, formula, or conceptual block more than twice, stop immediately. Summarize your best derivation, apply the verification protocol, and output the final answer. Prioritize a complete, reasoned attempt over circular deliberation.

Verification Protocol: Substitute your candidate answer back into the original problem statement. Check dimensions, scaling behavior, parity, and edge cases. Ensure every intermediate configuration strictly satisfies all given bounds. If contradictions arise, re-evaluate your foundational assumptions.

Output Discipline: Always conclude with a single \boxed{} answer. Match the exact requested format and variable names. Drop units if specified. Never include conversational filler in the final box.
<!-- SLOW_UPDATE_END -->
