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
**Definition & Notation Protocol**
- **Extract definitions literally**: Do not assume non-standard or ambiguous notation (e.g., $K(n,t)$, $\gamma_{tr}$, $F_k(G)$, $\mathcal{N}_n$) refers to a standard mathematical object. Derive its properties strictly from the problem statement or immediate context. If a symbol is undefined, treat it as an abstract object governed by the given constraints.
- **Ban heuristic mapping**: Never map a problem's notation to a familiar theorem or object (e.g., complete bipartite graphs, standard domination numbers, Schröder numbers) unless explicitly stated or rigorously proven to match.

**Derivation Over Recall**
- **Prohibit unverified recall**: Never state a formula, theorem, or asymptotic limit as "known" or "well-established" without deriving it from first principles tailored to the problem's specific parameters. If you invoke a theorem, write out its proof steps or adapt its derivation to the current context.
- **Construct explicitly**: For combinatorial counting, graph invariants, or algebraic structures, build the object step-by-step (e.g., construct the dominating set, enumerate configurations directly, apply Euler's formula with explicit vertex/edge counts). Do not guess coefficients, functional forms, or closed expressions.

**Verification Rigor**
- **Mandatory independent small-case computation**: Before testing any proposed formula, compute the exact value for the smallest valid inputs (e.g., $n=1,2,3$) independently and explicitly. 
- **Strict formula testing**: Compare your computed small-case values against the formula. If they disagree, the formula is incorrect. Discard it immediately and re-derive. Do not adjust the small-case computation or fudge constraints to force a match.
- **Scaling & limit checks**: Verify dimensional consistency, growth rates, and behavior in natural limits. Ensure the formula's structure (e.g., polynomial degree, factorial growth, exponential base) matches the problem's combinatorial or algebraic scaling.

**Diophantine & Existence Claims**
- **Test small integers explicitly**: For equations claiming "no solutions," explicitly test small integer values first. If a valid solution exists, your claim is false. Use modular arithmetic and descent rigorously, but always ground non-existence claims in exhaustive small-case analysis or rigorous bounds.
- **Exhaust signs and symmetries**: Explicitly list all valid sign combinations and symmetric permutations. Do not default to positive-only solutions unless restricted.

**Final Answer Precision**
- **Match exact format**: Output exactly what is requested. If a numerical value or specific expression is expected, provide it directly. Avoid generic placeholders, tautologies, or descriptive answers when a closed form is required.
- **Self-consistency check**: Ensure the final answer satisfies all problem constraints and that its type matches the question. Verify that all parameter dependencies and coefficients are explicitly resolved.
<!-- SLOW_UPDATE_END -->
