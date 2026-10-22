# Research Mathematics: Exact Answers

## Setup
- Restate exactly what quantity is asked for, and under which hypotheses.

## Solving
- **Ansatz & Scaling**: Distinguish regimes carefully. Traveling waves/solitons use $\xi = x - ct$. Diffusion/self-similarity uses $\xi = x/t^\beta$. Balance highest-order terms to derive scaling exponents systematically; do not guess.
- **Substitution & Parameter Balancing**: Substitute the ansatz directly into the equation. Collect terms by derivative order or asymptotic parameter. Set leading-order coefficients to zero to derive ODEs for profiles and algebraic equations for parameters (speed, amplitude, width).
- **Singular Perturbations & Boundary Layers**: For $\epsilon y'' + \dots = 0$, use matched asymptotic expansions. Find the outer solution ($\epsilon=0$). Identify layer location from the sign of the first-derivative coefficient ($a(x)>0 \Rightarrow$ left, $a(x)<0 \Rightarrow$ right). Rescale variables, solve inner equation, match limits, and construct the uniform approximation: $y_{\text{unif}} = y_{\text{outer}} + y_{\text{inner}} - y_{\text{match}}$.
- **WKB & Asymptotic Integrals**: Use standard forms (e.g., $y \sim Q^{-1/4} e^{\pm \epsilon^{-1} \int \sqrt{Q}}$). Carefully track amplitude/prefactor terms alongside the exponential phase. For Laplace-type integrals, find the true global maximum of the exponent by solving $S'(t)=0$ or checking boundaries. Expand strictly to the requested order; do not truncate prematurely.
- **Execution**: Solve resulting equations analytically. Eliminate arbitrary constants/undetermined functions unless permitted. Strictly adhere to constraints (e.g., 'do not approximate', 'only use given variables').

## Checking
- **Substitution Verification**: Plug the complete candidate solution back into the original equation. Confirm every term cancels or balances exactly (or to the required asymptotic order). If not, the parameters or ansatz are incorrect.
- **Boundary/Initial Conditions**: Explicitly evaluate the solution at all given limits, boundaries, and initial points. Ensure inner/outer limits match and far-field conditions are satisfied. Adjust integration constants accordingly.
- **Limit & Sign Analysis**: Verify asymptotic limits ($\epsilon \to 0$, $t \to \infty$) and symmetry properties. Check signs carefully, especially in logarithmic or integral terms where domain affects the sign.
- **Format & Completeness**: Ensure the expression contains only requested variables/constants, no undefined functions, and matches the requested format exactly. Reject trivial results (e.g., constants) that fail to capture expected profiles (boundary layers, wave shapes).

## Final Answer
- Provide a single, fully simplified closed-form expression.
- Ensure all constants are resolved numerically or in terms of the given parameters only.
- Format exactly as requested (e.g., inside `\boxed{}`, using specified variables).

<!-- SLOW_UPDATE_START -->
<!-- SLOW_UPDATE_END -->
