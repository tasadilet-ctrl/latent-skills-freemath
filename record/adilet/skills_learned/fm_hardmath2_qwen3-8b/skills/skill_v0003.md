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
- **Layer Location**: Evaluate the sign of $a(x)$ in $\epsilon y'' + a(x)y' + b(x)y = 0$ strictly on the domain. If $a(x) > 0$ everywhere, the layer is at the LEFT boundary. If $a(x) < 0$ everywhere, it is at the RIGHT boundary. NEVER skip the boundary layer step when $a(x)$ does not change sign.
- **Variable Coefficients**: Do not approximate $a(x)$ as constant near the layer unless explicitly justified. Solve the inner ODE exactly or use the exact integrating factor $\exp\left(\frac{1}{\epsilon}\int_{x_{\text{layer}}}^x a(s)\,ds\right)$. If $a(x)$ vanishes at the boundary, the layer thickness may differ from $\epsilon$; solve the dominant balance exactly.
- **Internal/Turning Point Layers**: If $a(x)$ changes sign inside the domain at $x_0$, an internal layer forms there. Linearize $a(x) \approx a'(x_0)(x-x_0)$ and use scaling $\xi = (x-x_0)/\sqrt{\epsilon}$. Solve the resulting inner ODE (often yielding error functions).
- **Uniform Approximation**: Always construct $y_{\text{unif}} = y_{\text{outer}} + y_{\text{inner}} - y_{\text{match}}$. Verify that $y_{\text{match}}$ is the common limit.

**WKB & Asymptotic ODEs**
- **First-Derivative Terms**: For $\epsilon^2 y'' + p(x)y' + q(x)y = 0$, first attempt to eliminate $p(x)y'$ via $y = z \exp\left(-\frac{1}{2\epsilon}\int p(x)dx\right)$ or check for exact integrability. Do not force standard WKB if it contradicts exact solvability.
- **Real Boundary/Initial Conditions**: When BCs are real and symmetric (e.g., $y'(0)=0$), you MUST combine the $\exp(\pm \frac{1}{\epsilon}\int \sqrt{Q})$ terms into $\cos\left(\frac{1}{\epsilon}\int_0^x \sqrt{Q(s)}\,ds\right)$ or $\sin\left(\frac{1}{\epsilon}\int_0^x \sqrt{Q(s)}\,ds\right)$. Never leave $\pm$ signs or separate exponentials in the final answer.
- **Amplitude Factor**: Always include the $Q(x)^{-1/4}$ prefactor. Verify it satisfies the original equation to leading order.

**Nonlinear PDEs & Traveling Waves**
- **Reaction-Diffusion Equations**: For $\partial_t u = \partial_{xx} u + f(u)$, ALWAYS use the traveling wave ansatz $\xi = x - vt$. Do not use diffusion scaling $\xi = x/\sqrt{t}$ unless dealing with pure conservation laws.
- **ODE Reduction**: After substituting $u(x,t) = U(\xi)$, integrate the resulting ODE with respect to $\xi$ as many times as possible. Use decay conditions at $\xi \to \pm\infty$ to set integration constants to zero BEFORE guessing a profile.
- **Profile Selection & Constant Resolution**: Match the profile power to the nonlinearity (e.g., cubic nonlinearities often yield $\text{sech}$, quadratic yield $\text{sech}^2$ or $\tanh$). Substitute the trial form, compute derivatives EXACTLY, and match coefficients algebraically. Solve for ALL parameters (amplitude, width, speed) explicitly. Do not leave arbitrary constants ($A, B, C$) in the final answer.
- **Format Compliance**: If the prompt requests exponential or rational forms, convert hyperbolic functions accordingly (e.g., $\text{sech}^2(z) = 4e^{2z}/(e^{2z}+1)^2$).

**Asymptotic Integrals**
- **Term-by-Term Integration**: For $\int_0^\infty [f(t) - \text{singular part}] e^{-xt} dt$, expand the bracketed term as a Taylor series in $t$. Integrate term-by-term using $\int_0^\infty t^n e^{-xt} dt = n!/x^{n+1}$. Keep terms up to the requested order.
- **Sign Tracking**: Track signs meticulously, especially in logarithmic denominators. For large $x$, $\ln(y/x) = \ln y - \ln x \approx -\ln x$. Do not drop the negative sign.
- **Variable Consistency**: Provide the final expansion in the variable requested by the problem (typically $x$). Do not switch to $z=1/x$ unless explicitly defined and consistently used in the prompt.
<!-- SLOW_UPDATE_END -->
