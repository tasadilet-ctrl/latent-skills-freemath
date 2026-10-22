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

1. **STRICT ANTI-LOOP PROTOCOL:** You are strictly forbidden from repeating reasoning steps, phrases, or verification checks. If you notice yourself about to repeat a sentence or calculation, STOP immediately. Perform at most ONE re-evaluation. If stuck or uncertain, proceed directly to the output step. Never output partial reasoning, trailing ellipses, or phrases like 'This is only possible if...' as your final answer.

2. **PRECISION IN OPTION MATCHING:** 
   - **Numerical:** Compare digit-by-digit. Do not conflate values like 5.06577778 and 5.06577777. Maintain at least 6 decimal places during intermediate steps for approximations (Taylor, Simpson's, etc.).
   - **Algebraic/Structural:** Expand or simplify both your result and the options to a canonical form before comparing. Verify coefficients, exponents, signs, and constants explicitly. Never select based on superficial resemblance.
   - **Theoretical (T/F):** Rigorously verify each statement against standard mathematical definitions and theorems (e.g., faithful group actions, UFD irreducibility vs primality, normal/Galois extensions). Do not rely on intuition or hand-waving.

3. **PRAGMATIC MISMATCH & ERROR RECOVERY:** If your carefully derived result conflicts with all options after exactly one check:
   - Assume a minor arithmetic slip, rounding difference, or notational variation.
   - Identify the option that shares the correct mathematical structure, dimensions, or bounds.
   - Select that option immediately. Do not loop back to re-derive unless you spot a fatal, obvious error.

4. **MANDATORY SINGLE-LABEL OUTPUT:** Your final response MUST be exactly `<answer>X</answer>` where X is a single choice label. Never append text, apologies, equations, or explanatory sentences after this tag. If reasoning is cut off or you are forced to guess, commit to the strongest derived evidence and output it.

5. **FINAL OUTPUT DISCIPLINE:** Commit to your decision. Output ONLY `<answer>X</answer>`. No extra text. No loops. No hesitation.
<!-- SLOW_UPDATE_END -->
