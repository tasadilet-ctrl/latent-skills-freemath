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
When differentiating composite or rational functions, explicitly write the derivative of each nested component or factor before combining. After combining, simplify the expression algebraically before substituting numerical values to prevent factor loss, sign errors, or chain rule mistakes.

If your computed result does not exactly match any option, do not guess the 'closest' value. Instead, immediately re-verify your parameter extraction (e.g., '5% remains' means multiply by 0.05, not 0.95), check your initial setup against the problem statement, and re-derive the solution from scratch. Only select an option if it precisely matches your verified result.

For numerical integration methods (Midpoint, Trapezoidal, Simpson's), maintain at least 6 decimal places for all intermediate function evaluations. Recompute the final sum carefully to prevent rounding drift from compounding across subintervals.

When evaluating polynomials, determinants, or large arithmetic products, compute in smaller verified steps and check orders of magnitude. Do not guess eigenvalues or polynomial roots; derive them systematically via row reduction or characteristic equation expansion.

Always explicitly state sign conventions, force directions, and percentage interpretations before writing equations. Cross-check your final computed value against mathematical or physical constraints (e.g., probabilities ≤ 1, positive magnitudes, bounded velocities) before matching to options.
<!-- SLOW_UPDATE_END -->
