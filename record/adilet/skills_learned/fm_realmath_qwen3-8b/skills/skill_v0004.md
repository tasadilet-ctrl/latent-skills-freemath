# Research Mathematics: Exact Answers

## Setup
- Restate exactly what quantity is asked for.
- Explicitly list and isolate all hypotheses, constraints, and domains (e.g., coprimality, exponent bounds, support conditions).

## Solving
- Derive the answer rigorously step-by-step from the problem's explicit definitions and constraints. Do not guess, assume simple forms, or rely on intuition alone.
- When invoking a theorem or known result, state it precisely and verify that all its hypotheses match the problem's conditions. If a formula is recalled, derive or justify it briefly rather than assuming it holds universally.
- Track all numerical constants, combinatorial factors, dimensional dependencies, and intermediate results explicitly.
- If the derivation stalls or becomes repetitive, backtrack immediately rather than looping.

## Checking
- **Mandatory small-case & limit verification**: Independently compute exact values for small inputs or trivial configurations. Verify behavior in natural limits (e.g., $n\to\infty$, parameters $\to 0$ or $1$). The formula must remain well-defined and match intuition.
- **Structural & dimensional checks**: Verify dimensional consistency, scaling behavior, and exact coefficients against known formulas. Check sign symmetries and multi-valued function branches (e.g., Lambert $W$, logarithms) based on domain/range constraints.
- **Validation & arithmetic**: Validate any cited theorem or recalled formula against the problem's specific parameters. Re-check arithmetic and logical deductions step-by-step to avoid algebraic slips.
- **Type & constraint match**: Ensure the derived answer satisfies all problem constraints and that its type matches the question (e.g., numerical value vs. descriptive statement). Avoid tautological or placeholder answers.

## Final Answer
- Output exactly what is requested: a closed-form formula, a precise numerical range, or a complete descriptive statement. Ensure all valid sign combinations and parameter dependencies are included.
- Avoid placeholders or ambiguous notation; if a quantity is proven non-existent, state it clearly in words or standard mathematical notation rather than using '0'.
- Box only the final, fully resolved answer. Format strictly as `Answer: $\boxed{<answer>}$` containing only the final result. Ensure it is self-contained, fully simplified, and directly answers the question.

<!-- SLOW_UPDATE_START -->
**Form & Expression Strictness**
- **Preserve requested functional forms**: If the prompt specifies an answer "in terms of [specific function/variable]", output exactly that form. Do not evaluate constants (e.g., leave $\zeta(2)$ as $\zeta(2)$) or substitute equivalent expressions unless explicitly instructed.
- **Infer missing context**: When notation is undefined or appears truncated, do not output "Undefined". Infer the intended object from surrounding mathematical context, standard literature in the subfield, or structural patterns. Proceed with the most plausible standard interpretation and state your assumption briefly.

**Recall & Verification Balance**
- **Leverage known results responsibly**: For advanced theorems or specialized formulas, recall the standard result if the notation matches literature. Do not force first-principles derivation when it is infeasible. Instead, immediately verify the recalled formula against small cases, limits, or dimensional scaling.
- **Cross-check coefficients**: When recalling or deriving formulas, explicitly verify numerical coefficients and signs against trivial cases or known identities. Do not assume coefficients are 1 or follow simple patterns without verification.

**Diophantine & Modular Arithmetic Rigor**
- **Avoid flawed modular shortcuts**: When using modular arithmetic to rule out solutions, carefully enumerate all residue classes, particularly distinguishing even/odd cases. A single modulus is rarely sufficient; if it does not yield a contradiction, switch to a different modulus or bound analysis.
- **Extend systematic searches**: Do not terminate a search for integer solutions after testing only the smallest values. If no solution is found quickly, apply theoretical bounds (e.g., growth rates, inequalities) to justify non-existence, or extend the search range systematically. Never claim "no solutions" based on an incomplete search or a single modular check.

**Final Answer Completeness & Formatting**
- **Address all sub-questions**: If the prompt asks for multiple quantities or properties, list each explicitly in the final answer. Do not merge them or output only one.
- **Validate constraints before boxing**: Ensure the final answer strictly satisfies all stated constraints (e.g., primitivity, non-triviality, domain restrictions). If a candidate answer violates a constraint, discard it immediately and re-evaluate.
<!-- SLOW_UPDATE_END -->
