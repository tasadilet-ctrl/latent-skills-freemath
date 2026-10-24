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

1. ABSOLUTE PROHIBITION ON UNVERIFIED CITATIONS. Never invoke a theorem, author, paper, or 'classical result' to justify a step. If you recall a result, you must derive it from scratch or verify it against the prompt's exact definitions before using it. If you cannot derive it, discard the recalled result immediately and proceed with first-principles reasoning. Assume the problem is entirely self-contained.

2. MANDATORY DEFINITION MAPPING & SMALL-CASE TESTING. Before any algebraic manipulation, explicitly translate every term in the prompt into precise mathematical objects. Immediately test these definitions on trivial instances (e.g., n=1, n=2, empty set, single edge, p=1). If your interpretation yields a contradiction or degeneracy in the trivial case, your definition mapping is wrong. Correct it before proceeding.

3. FIRST-PRINCIPLES CONSTRUCTION OVER PATTERN MATCHING. Do not guess constants, exponents, or thresholds based on superficial similarity to known problems. Construct the solution explicitly: enumerate small cases, build extremal examples, or perform direct combinatorial/analytic counting. Verify that your constructed example satisfies all prompt constraints before generalizing.

4. RIGOROUS SCALING & DIMENSIONAL VERIFICATION. For any expression involving exponents, asymptotic bounds, or mathematical constants, explicitly verify scaling behavior and dimensional consistency. Substitute trivial limits (e.g., dimension=1, probability=0, degree=2) into your derived formula. If the limit yields impossible values (e.g., negative counts, probability > 1, wrong growth rate, or violates a stated bound), the formula is incorrect. Halt and re-derive.

5. STRICT CONSTRAINT VALIDATION & LOOP PREVENTION. After each step, verify that intermediate results respect all problem constraints (integrality, positivity, graph properties, field characteristics). If you find yourself repeating the same justification or backtracking more than twice, stop immediately. Discard the current path, return to the explicitly mapped definitions, and restart the derivation using a different method (e.g., switch from algebraic to combinatorial, or from general theory to case analysis).

6. FINAL ANSWER FORMAT. Output exactly one closed-form expression or number in \boxed{}. Ensure it matches the requested format precisely, with no extraneous text, alternative answers, or explanatory remarks inside the box.
<!-- SLOW_UPDATE_END -->
