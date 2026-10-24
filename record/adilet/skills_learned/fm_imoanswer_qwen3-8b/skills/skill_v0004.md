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
Verification Trap Avoidance: Do not discard a structurally sound candidate based on a single arithmetic slip during checking. If verification yields a contradiction, re-calculate the specific step explicitly. Only reject the candidate if the contradiction persists after careful re-evaluation. Treat verification as a debugging tool, not a pass/fail gate.

Hard Anti-Looping Enforcement: If you repeat a phrase, calculation, or logical branch more than twice, HALT immediately. You are in a reasoning loop. Summarize your best derivation, force a conclusion, and output the answer. Never sacrifice completion for exhaustive checking. Set a strict limit of 3 case tests before generalizing algebraically.

Geometry Execution Discipline: Never invoke symmetry, regularity, or special configurations (e.g., cyclic, isosceles, parallel lines) without explicit proof. Use coordinates or vectors to ground every point and line. Verify each geometric transition against the problem's constraints. If coordinates become complex, simplify algebraically before substituting numerical values.

Exact Form & Output Mandate: Decimal approximations are strictly forbidden. Convert all intermediate decimals to fractions or radicals immediately. Ensure your final answer is fully simplified and matches the requested format. Always conclude with a single \boxed{}. If you approach the token limit, output your strongest candidate immediately rather than continuing to check.
<!-- SLOW_UPDATE_END -->
