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
Final Answer Formatting: Place ONLY the final mathematical value or expression inside \boxed{}. Never include descriptive text, conversational phrases, or units (e.g., drop ^\circ if the problem asks for a value 'in degrees'). If an equation is requested, present it in a standard simplified form (e.g., polynomial = 0 or variable = expression). Match the exact variable names requested.

Geometric Reasoning: Do not assume symmetry, regularity, or special configurations (e.g., equilateral, regular tetrahedron) unless explicitly stated or rigorously derived. Use coordinates, vectors, or trigonometric identities to derive properties from the given constraints. Verify that your constructed configuration satisfies all conditions before extracting the answer.

Algebraic & Combinatorial Rigor: Track signs meticulously in sums, products, and inequalities. When estimating bounds or evaluating series, verify the direction of each inequality step-by-step. Do not invoke vague 'known results' or guess constants. Derive counting arguments from first principles, small cases, or generating functions. If a direct approach stalls, explicitly construct examples or compute partial sums to find patterns.

Verification Protocol: Before finalizing, substitute your candidate answer back into the original constraints. Check dimensions, parity, scaling behavior, and edge cases. If your derivation yields a sign or magnitude that contradicts basic bounds, re-evaluate your assumptions immediately.

Output Discipline: Always conclude with a single \boxed{} answer. Avoid repetitive reasoning loops. If a step does not yield progress, backtrack and switch to a concrete computational method (e.g., coordinate geometry, explicit enumeration, or asymptotic estimation) rather than circling the same conceptual step.
<!-- SLOW_UPDATE_END -->
