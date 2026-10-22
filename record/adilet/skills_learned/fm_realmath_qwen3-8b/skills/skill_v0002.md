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
**Derivation & Verification Protocol**
- **Prohibit unverified recall**: Never state a formula, theorem, or asymptotic limit as "known" or "well-established" without deriving it from first principles or verifying it against at least two small cases (e.g., $n=1,2$ or trivial parameters). If a recalled formula fails small-case testing, discard it immediately and re-derive.
- **Mandatory small-case calibration**: For any proposed closed-form expression involving parameters, compute the exact value for the smallest valid inputs. Adjust coefficients, indices, and scaling factors until the formula matches. This catches off-by-one errors, incorrect bases, and wrong asymptotic constants.

**Asymptotics & Limits**
- **Do not rely on generic intuition**: Avoid shortcuts like "connected structures dominate" or "random graphs behave typically" unless explicitly proven for the specific combinatorial class. Use generating functions, exact counting recurrences, or precise asymptotic expansions. Verify limits by analyzing the ratio of leading terms or known series expansions.

**Algebraic & Diophantine Problems**
- **Structural methods over brute force**: Do not search for solutions by trial and error. Use modular arithmetic, factorization in appropriate rings (e.g., $\mathbb{Z}[\sqrt{d}]$), unique factorization properties, and growth bounds to constrain solutions rigorously.
- **Exhaust signs and symmetries**: Explicitly list all valid sign combinations ($\pm$) and symmetric permutations that satisfy the equation. Do not default to positive-only solutions unless the problem explicitly restricts the domain. Verify primitivity conditions ($\gcd=1$) rigorously for each candidate.

**Notation & Definitions**
- **Infer from context, do not guess**: If notation is non-standard or undefined, derive its properties mathematically from the problem's structural clues, generating functions, or recurrence relations. Do not guess standard names or refuse to answer; treat the symbol as an abstract object governed by the given constraints.

**Final Answer Completeness**
- Ensure the boxed answer includes all valid cases, sign variations, exact coefficients, and parameter dependencies. Never output placeholders, generic variables, or "cannot be determined" unless a formal proof of impossibility is explicitly derived.
<!-- SLOW_UPDATE_END -->
