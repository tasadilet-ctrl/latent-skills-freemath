# Mathematics: Multiple Choice

## Setup
- Restate exactly what quantity or statement is asked for, and under which hypotheses.

## Solving
- Convert the problem to its standard mathematical form (e.g., leading coefficient 1 for ODEs, alphabetical vertex correspondence for similarity) before applying any theorem or formula.
- Maintain a consistent direction for all ratios and proportions throughout the calculation.
- Explicitly state the theorem, formula, or method applied at each step.
- Show each algebraic, calculus, or numerical step explicitly; maintain exact symbolic forms and simplify before substituting numerical values to avoid compounding rounding errors.

## Checking
- Verify your derivation by testing a special case, limit, or small instance.
- Substitute your computed value back into the original equation or condition to verify it satisfies all constraints.
- Check units, dimensions, and physical plausibility (e.g., magnitudes must be positive, velocities bounded by terminal limits).
- Explicitly compare your final computed value with each option's value. Ensure precision and units match the question's requirements.
- If answer choices are numerical approximations, ensure your precision is sufficient to distinguish between close options.
- If the result does not appear among the choices, re-derive carefully from the start instead of guessing or adjusting the answer.

## Final Answer
- Compare your verified result exactly with the given options. Do not alter, truncate, or "clean up" an option to force a match.
- Select only the label of the option that precisely equals your result.
- Output ONLY that label inside the tags. Do not include explanations, numbers, units, or LaTeX inside <answer>...</answer>.
- Example: <answer>D</answer>

<!-- SLOW_UPDATE_START -->
When outputting your final answer, strictly use the format <answer>X</answer> on a new line. Never wrap your final label in $$, \boxed{}, or any other LaTeX container. This ensures correct parsing.

For linear differential equations and Wronskian problems, always divide by the leading coefficient first to achieve the standard form y'' + p(t)y' + q(t)y = 0 before identifying p(t). Apply Abel's identity exactly as W(t) = C exp(-∫ p(t) dt). Do not skip the division step, as misidentifying p(t) leads to incorrect exponential factors.

When computing logarithms, exponentials, or solving transcendental equations numerically, verify every intermediate value. For logs, check that ln(a/b) = ln(a) - ln(b) matches your calculator output. For numerical roots, substitute your computed value back into the original equation to confirm it satisfies the equality within tolerance. Do not proceed with an unverified numerical approximation.

For probability problems involving biased random walks reaching a target level m, use the first-passage probability formula P(reach m) = (p/q)^m when p < q, not p^m. Verify the drift direction and formula applicability before computing.

When a problem asks for the "highest" or "lowest" possible value over a graph class, do not assume a symmetric or regular graph automatically yields the optimum. Explicitly evaluate candidate topologies (e.g., star, path, complete, cycle) with the given edge/node constraints to find the true extremum.

When matching derived lists or sets to options, verify each element individually against your criteria. Reject options containing even one invalid element, and do not select a list simply because it looks similar to your result.

If your computed result does not match any option, do not guess the closest value. Re-verify parameter extraction, check your initial setup, and re-derive from scratch. For numerical integration, maintain at least 6 decimal places. Always state sign conventions and cross-check physical/mathematical constraints before final selection.
<!-- SLOW_UPDATE_END -->
