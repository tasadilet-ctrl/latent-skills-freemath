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
**Boundary Layers & Singular Perturbations**
- For $\epsilon y'' + a(x)y' + b(x)y = 0$, solve the reduced equation $a(x)y_0' + b(x)y_0 = 0$ for the outer solution.
- Locate the boundary layer strictly by the sign of $a(x)$: if $a(x) > 0$ on the domain, the layer is at the left boundary; if $a(x) < 0$, it is at the right boundary. If $a(x)$ vanishes inside the domain, use turning point scaling $\xi = x/\sqrt{\epsilon}$.
- Rescale near the layer: $\xi = (x - x_{	ext{layer}})/\epsilon$. Solve the inner ODE, keeping only dominant terms.
- Match limits: $\lim_{\xi 	o \infty} y_{	ext{inner}} = \lim_{x 	o x_{	ext{layer}}} y_{	ext{outer}}$.
- Construct the uniform approximation strictly as $y_{	ext{unif}} = y_{	ext{outer}} + y_{	ext{inner}} - y_{	ext{match}}$. Never omit the exponential boundary layer term in the final answer.

**WKB & Asymptotic ODEs**
- For $\epsilon^2 y'' + Q(x)y = 0$, the leading-order WKB approximation is $y(x) \sim \frac{C}{Q(x)^{1/4}} \exp\left(\pm \frac{1}{\epsilon} \int^x \sqrt{Q(s)} \, dsight)$. Always include the $Q(x)^{-1/4}$ amplitude factor.
- If boundary conditions are real, combine exponential terms into $\cos$ or $\sinh$ functions. Determine constants by applying BCs to the full expression.
- If a first-derivative term exists, check if the equation admits an exact solution or can be transformed. Do not force a standard WKB form if it leads to contradictions.

**Nonlinear PDEs & Traveling Waves**
- Treat "soliton behavior" or "self-similarity" prompts as traveling wave problems $u(x,t) = U(\xi)$ with $\xi = x - vt$, unless conservation laws explicitly require $x/t^eta$ scaling.
- Substitute derivatives immediately: $u_t = -v U'$, $u_x = U'$, $u_{xx} = U''$. Integrate once if the equation allows (set integration constant to zero using decay BCs).
- Do not guess ansatz parameters. Substitute a trial form (e.g., $A 	ext{sech}^k(B\xi)$), compute derivatives exactly, and match coefficients algebraically to solve for $A$, $B$, and $v$.
- Verify the candidate solution satisfies the original PDE exactly before finalizing.

**Asymptotic Integrals**
- For $I(x) = \int_x^\infty f(t) e^{-g(t)} \, dt$ as $x 	o \infty$, use repeated integration by parts centered at the lower limit. The expansion is $I(x) \sim \frac{e^{-g(x)}}{g'(x)} \left[ f(x) - \frac{d}{dx}\left(\frac{f(x)}{g'(x)}ight) + \cdots ight]$.
- Do not approximate or expand denominators (e.g., $1+t^5$) unless explicitly permitted. Keep exact functional forms in the series terms.
- For integrals involving $t+x$ in the denominator, use substitutions like $t = xu$ or recognize Gamma function identities carefully. Double-check prefactors and limits.
<!-- SLOW_UPDATE_END -->
