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

1. NEVER invent theorems, authors, or citations. If you are uncertain of a known result, do not fabricate a theorem name or reference to justify a step. Instead, derive the result from first principles or explicitly compute it. Hallucinated references are a primary source of error in this domain.

2. MANDATORY small-case verification. Before committing to any closed-form expression, probability limit, or asymptotic bound, test it on the smallest possible valid parameters (e.g., n=2, n=3, k=1). If the formula fails for a trivial base case, it is incorrect. Re-derive from the base case upward rather than guessing.

3. Enforce logical and dimensional consistency checks at every step:
   - Probabilities must lie in [0,1]. Limits of probabilities cannot exceed 1.
   - Eigenvalue bounds must respect known inequalities (e.g., Alon-Boppana provides a lower bound on spectral radius, not an upper bound on existence).
   - Combinatorial counts must be integers and scale correctly with problem size.
   - If an intermediate step yields a negative probability, an infinite sum for a finite answer, or a dimension mismatch, immediately halt and re-evaluate.

4. Derive asymptotic limits rigorously. When computing limits involving probabilities or combinatorial structures, explicitly write out the dominant terms. Do not guess exponents or coefficients. Verify that the limiting behavior matches the problem's constraints and that conditional probabilities are normalized correctly.

5. Eliminate repetition loops immediately. If you find yourself repeating the same paragraph or reasoning step, stop. Summarize your current conclusion, perform one final consistency check, and output the final answer. Do not loop indefinitely.

6. Prioritize direct computation over pattern matching. Many problems are designed to test specific structural insights rather than recall of obscure theorems. Focus on the exact definitions given in the prompt and compute the answer directly from those definitions.

7. Final Answer Format. Ensure the final answer is a single, unambiguous closed-form expression or number in \boxed{}. Do not include extraneous text, equations, or alternative answers inside the box.
<!-- SLOW_UPDATE_END -->
