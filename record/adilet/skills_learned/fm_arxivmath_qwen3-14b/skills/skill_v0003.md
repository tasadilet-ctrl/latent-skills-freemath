# Research Mathematics: Exact Answers

## Setup
- Restate exactly what quantity is asked for, and under which hypotheses.

## Solving
- Choose a method that can actually produce that quantity; note which known result each step uses.

## Checking
- Test the answer against a special case, a limit, or a small instance before committing.

## Final Answer
- Give one closed-form answer in the requested form.

<!-- SLOW_UPDATE_START -->
When solving research-level mathematics problems, strictly adhere to the following strategic directives:

1. ZERO TOLERANCE FOR UNVERIFIED CITATIONS. Never cite a theorem, author, paper, or 'classical result' to justify a step unless you explicitly derive it or verify it against the problem's exact hypotheses. If a recalled result conflicts with a direct derivation from the prompt's definitions, discard the recalled result immediately. Assume the problem is self-contained.

2. DERIVE EXCLUSIVELY FROM PROMPT DEFINITIONS. Begin by explicitly listing the definitions, constraints, and quantities requested. Build every step from these definitions. Do not jump to a standard formula or analogous problem without proving it applies to the specific conditions given (e.g., characteristic restrictions, minor-free classes, boundary conditions).

3. MANDATORY SCALING & DIMENSIONAL ANALYSIS. For any answer involving exponents, asymptotic bounds, or physical/mathematical constants, explicitly verify dimensional consistency and scaling behavior. Test the derived expression against trivial limits (e.g., n=1, p=0, d=2) and ensure units/bounds align with the problem structure. If scaling fails or yields impossible values (e.g., probability > 1, negative counts, wrong growth rate), the formula is incorrect. Re-derive immediately.

4. CONSTRUCTIVE EXTREMAL VERIFICATION. When asked for maximums, minimums, thresholds, or exact constants, construct the extremal example or compute the value from first principles. Do not guess based on pattern matching. Prove tightness by exhibiting a valid configuration that achieves the bound.

5. STRICT CONSTRAINT VALIDATION AT EVERY STEP. After each algebraic manipulation or combinatorial count, verify that the intermediate result respects all problem constraints (e.g., integrality, positivity, characteristic conditions, graph properties). If a step violates a constraint or produces a contradiction, halt and backtrack.

6. FINAL ANSWER FORMAT. Output exactly one closed-form expression or number in \boxed{}. Ensure it matches the requested format precisely, with no extraneous text or alternative answers inside the box.
<!-- SLOW_UPDATE_END -->
