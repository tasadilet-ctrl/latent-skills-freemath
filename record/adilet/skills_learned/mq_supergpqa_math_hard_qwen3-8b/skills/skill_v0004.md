# Mathematics: Multiple Choice

## Setup
- Restate exactly what quantity or statement is asked for, and under which hypotheses.

## Solving
- Work the problem out step-by-step, noting which known result each step uses. Briefly verify constraints (e.g., positivity, symmetry, boundaries) at major steps.
- Decompose complex or multi-part problems into sequential sub-steps and solve each independently.
- Explicitly state the theorem, identity, or algebraic manipulation used for each transformation.
- For complex expressions or recurring patterns, test a simple ansatz or compute initial terms/values to guide the derivation.
- If a calculation becomes complex, look for simplifications or alternative approaches. Avoid repetitive self-correction; commit to a derived path and proceed.

## Checking
- Test the result against a special case, limit, or small instance. Cross-validate using an independent method, bound, parity check, or symmetry argument.
- Verify via inverse operations (e.g., substitute back, check normalization/boundaries) and dimensional/unit consistency.
- Simplify the final expression and convert formats (e.g., radicals, fractions, decimals) to exactly match the structure of the answer choices.
- Systematically compare the simplified result against each option; use numerical estimation or boundary checks if options are numerically close.
- If the result conflicts with the options or no option matches, **stop and re-examine your setup and calculations step-by-step**. Identify likely errors (signs, constants, misapplied theorems) and correct them. Do not guess or force a match.
- Avoid infinite verification loops; once satisfied or if stuck, proceed to matching.

## Final Answer
- Simplify your derived result and plausible options to a canonical form. Compare term-by-term or coefficient-by-coefficient, recognizing mathematically equivalent notations.
- Match the verified result to the exact option. If approximation is required, select the closest valid option. Do not match based on superficial similarity.
- Output **only** the single choice label inside `<answer>` tags (e.g., `<answer>A</answer>`). Do not repeat reasoning or enter loops.
- If the computed value does not appear in the choices, re-evaluate your derivation before outputting; do not guess. If reasoning is cut off or loops, force an output based on the strongest derived evidence.

<!-- SLOW_UPDATE_START -->
**STRATEGIC DIRECTIVES FOR MATHEMATICAL PROBLEM SOLVING**

1. **STRICT ANTI-LOOP & COMMITMENT PROTOCOL:** You are strictly forbidden from repeating reasoning steps, re-deriving calculations, or outputting phrases like 'Rechecking the problem again,' 'But this is not the correct answer,' or 'This is not among the choices.' If your derivation yields a result, trust it. If it conflicts with options, perform at most ONE quick sanity check (e.g., bounds, dimensions, special case). Then commit to the closest option or the one with matching structure. Never loop back to re-solve. Stop generating reasoning immediately once you select an answer.

2. **NOTATION & MATHEMATICAL EQUIVALENCE:** 
   - Recognize standard equivalent notations immediately. In probability, $AB$ means $A \cap B$, and $A+B$ often means $A \cup B$. In algebra/geometry, different forms of the same equation (e.g., expanded vs. factored, slope-intercept vs. standard form) are identical. Do not discard options due to superficial notation differences.
   - When matching options, convert both your result and the choices to a canonical form (e.g., fully expanded, simplified fractions, or decimal) before comparing.

3. **NUMERICAL & SEQUENCE VERIFICATION:**
   - **Numerical Integration (Simpson's/Trapezoidal):** Explicitly verify $\Delta x = (b-a)/n$ and the weight pattern (1, 4, 2, 4, ..., 1) before summing. Maintain at least 6 decimal places. If your result is far from all options, re-evaluate the integrand or bounds immediately.
   - **Sequences & Series:** Do not blindly assume a known sequence (e.g., Catalan, Fibonacci). Compute the first 2-3 terms from the problem's definition explicitly. Compare these computed terms against the answer choices to confirm the pattern before applying a closed-form formula.

4. **PRAGMATIC MISMATCH & ERROR RECOVERY:** If your carefully derived result does not match any option after one check:
   - Assume a minor arithmetic slip, rounding difference, or notational variation.
   - Identify the option that shares the correct mathematical structure, dimensions, bounds, or initial terms.
   - Select that option immediately. Do not guess randomly, but do not force a re-derivation.

5. **MANDATORY SINGLE-LABEL OUTPUT:** Your final response MUST be exactly `<answer>X</answer>` where X is a single choice label. Never append text, apologies, equations, or explanatory sentences after this tag. If reasoning is cut off or you are forced to guess, commit to the strongest derived evidence and output it. No extra text. No loops. No hesitation.
<!-- SLOW_UPDATE_END -->
