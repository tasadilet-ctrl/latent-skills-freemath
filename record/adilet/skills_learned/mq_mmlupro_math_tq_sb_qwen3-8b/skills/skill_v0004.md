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

If you detect yourself repeating the same sentence, step, or correction loop more than twice, immediately halt the repetition. Commit to your current best derivation, perform one final verification, and output the answer. Do not get stuck in infinite reasoning cycles.

For linear differential equations and Wronskian problems, always divide by the leading coefficient first to achieve standard form before identifying coefficients. For damped oscillatory responses y(t) = A e^{-\alpha t} \sin(\omega t + \phi), do not assume the peak value equals the initial amplitude A. You must evaluate the exponential decay factor e^{-\alpha t_{peak}} at the time of the first maximum to find the true peak.

When computing logarithms, exponentials, or solving transcendental equations numerically, verify every intermediate value. For numerical roots, substitute your computed value back into the original equation to confirm it satisfies the equality within tolerance.

A regular n-gon is constructible with compass and straightedge if and only if n = 2^k \cdot p_1 \cdots p_m, where k \ge 0 and p_i are DISTINCT Fermat primes. The only known Fermat primes are 3, 5, 17, 257, and 65537. Do not include primes like 7, 11, 13, or 19. Only consider n \ge 3 as valid polygons.

Always verify the sign of your final computed result against the options. Selecting an option with the correct magnitude but the wrong sign is incorrect. Double-check derivative signs and algebraic subtractions.

For sets defined by restricted digit expansions (e.g., base 4 using only digits 0 and 1), recognize them as Cantor-like fractals. Their Lebesgue measure is 0, not the length of the bounding interval. Do not treat them as continuous intervals.

For exponential distributions, carefully distinguish between the rate parameter \lambda and the mean parameter \theta. If the problem states \theta = c, then E[X] = c. If it states \lambda = c, then E[X] = 1/c. Verify the parameterization context before computing expectations of min/max variables.

When computing covariance or variance from data lists, explicitly map which values correspond to which variable. Ensure you are pairing the correct observations. Use the sample formula \frac{1}{n-1}\sum(x_i-\bar{x})(y_i-\bar{y}) unless the problem specifies population parameters.

When asked to evaluate a polynomial f(x) at a scalar value (e.g., f(99)), do not confuse this with the matrix equation f(A) = 0. Compute the polynomial's coefficients explicitly first, then substitute the scalar.

If your computed result does not match any option, do not guess the closest value. Re-verify parameter extraction, check your initial setup, and re-derive from scratch. For numerical integration, maintain at least 6 decimal places. Always state sign conventions and cross-check physical/mathematical constraints before final selection.
<!-- SLOW_UPDATE_END -->
