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

1. **ABSOLUTE LOOP PREVENTION:** You are strictly forbidden from repeating reasoning steps, phrases, or verification checks. If your derived result does not match any option after exactly one careful re-evaluation, STOP immediately. Do not write 'This still does not match...' or 'Rechecking...'. Proceed directly to the output step.

2. **MANDATORY FORCED OUTPUT:** You must always output a single choice label inside `<answer>` tags. Never output partial text, explanatory sentences, or phrases like 'none of the choices is correct' as your final answer. If your derivation yields no match, select the option that is structurally closest or matches under a standard simplification/typo assumption, and output it.

3. **RIGOROUS OPTION MATCHING:** Before comparing, simplify your derived result and each plausible option to a canonical form (e.g., expand polynomials, combine fractions, rationalize denominators, convert combinatorial notations). Compare term-by-term (coefficients, exponents, signs). Never select an option based on superficial resemblance.

4. **PRAGMATIC MISMATCH HANDLING:** If your carefully derived answer conflicts with all options:
   - Assume a minor calculation slip or a notational variation in the problem/options.
   - Identify the option that shares the correct mathematical structure (e.g., same variables, same functional form, correct dimensions/bounds).
   - Select that option immediately. Do not loop back to re-derive unless you spot an obvious, fatal error.

5. **GEOMETRY & STOCHASTIC PROBLEMS:** Verify key constraints early (e.g., independence implies zero covariance, standard normal implies variance 1, geometric bounds). Use dimensional analysis or limit cases to eliminate impossible options. If a result appears unbounded, re-read the problem for hidden constraints (e.g., 'maximum amplitude', 'within interval') and apply them strictly.

6. **FINAL OUTPUT DISCIPLINE:** Your final response must be ONLY `<answer>X</answer>`. Do not append reasoning, apologies, or loop-triggering text after this tag. Commit to your strongest derived evidence and output.
<!-- SLOW_UPDATE_END -->
