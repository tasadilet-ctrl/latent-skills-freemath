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
<!-- SLOW_UPDATE_END -->
