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
- **Layer Location & Scaling**: For $\epsilon y'' + a(x)y' + \dots = 0$, if $a(x)$ does not change sign, the layer is at the boundary where $a(x)$ points inward ($a>0 \Rightarrow$ left, $a<0 \Rightarrow$ right). Use scaling $\xi = (x-x_{	ext{layer}})/\epsilon$. If $a(x)$ vanishes at $x_0$ inside the domain, an internal layer forms. Linearize $a(x) \approx a'(x_0)(x-x_0)$ and use scaling $\xi = (x-x_0)/\sqrt{\epsilon}$.
- **Inner ODE Solution**: Solve the rescaled inner ODE exactly. For internal layers, this often yields error functions or Gaussians.
- **Matching Constants**: Determine integration constants by matching limits: $\lim_{\xi 	o -\infty} y_{	ext{inner}} = y_{	ext{outer, left}}$ and $\lim_{\xi 	o +\infty} y_{	ext{inner}} = y_{	ext{outer, right}}$. Construct the uniform approximation as $y_{	ext{unif}} = y_{	ext{outer}} + y_{	ext{inner}} - y_{	ext{match}}$.

**WKB & Asymptotic ODEs**
- **Standard Form & Amplitude**: Rewrite equations as $\epsilon^2 y'' = Q(x) y$ (eliminate first-derivative terms via $y=z e^{-\frac{1}{2\epsilon}\int p}$ if present). The leading-order amplitude is ALWAYS $Q(x)^{-1/4}$.
- **General Solution & ICs**: Write $y(x) \sim Q(x)^{-1/4} \left[ C_1 \exp\left(\frac{1}{\epsilon}\int_{x_0}^x \sqrt{Q(s)}\,dsight) + C_2 \exp\left(-\frac{1}{\epsilon}\int_{x_0}^x \sqrt{Q(s)}\,dsight) ight]$. Use given initial/boundary conditions to solve for $C_1$ and $C_2$ algebraically. NEVER leave arbitrary constants in the final answer.
- **Symmetric/Antisymmetric Conditions**: If conditions imply symmetry ($y'(0)=0$), combine terms into $\cos\left(\frac{1}{\epsilon}\int \sqrt{Q}ight)$. If antisymmetric ($y(0)=0$), combine into $\sin\left(\frac{1}{\epsilon}\int \sqrt{Q}ight)$. Explicitly evaluate the phase integral $\int \sqrt{Q(s)}\,ds$.

**Nonlinear PDEs & Traveling Waves**
- **Ansatz Selection**: For reaction-diffusion equations $\partial_t u = \partial_{xx} u + f(u)$, strictly use the traveling wave ansatz $u(x,t)=U(x-vt)$. NEVER use self-similarity scaling ($x/t^eta$) for these equations.
- **ODE Reduction**: Substitute the ansatz to get an ODE in $\xi$. Integrate with respect to $\xi$ as many times as possible. Use decay/boundary conditions at $\xi 	o \pm\infty$ to set integration constants to zero.
- **Profile Matching**: Guess a trial profile (e.g., $	ext{sech}$, $	ext{sech}^2$, $	anh$). Compute derivatives EXACTLY. Substitute into the ODE and match coefficients of linearly independent functions (e.g., $	ext{sech}^2$, $	ext{sech}^4$, $	anh 	ext{sech}^2$) algebraically to solve for amplitude, width, and speed. Do not guess parameters; derive them.
- **Format Compliance**: If the prompt requests exponential or rational forms, convert hyperbolic functions explicitly (e.g., $	ext{sech}(z) = 2/(e^z + e^{-z})$).

**Asymptotic Integrals**
- **Term-by-Term Expansion**: For $\int_0^\infty g(t) e^{-xt} dt$, expand $g(t)$ as a Taylor series in $t$ around $0$. Integrate term-by-term using $\int_0^\infty t^n e^{-xt} dt = n!/x^{n+1}$.
- **Sign & Order Tracking**: Track signs meticulously, especially from logarithmic expansions or alternating series. Expand strictly to the requested order in $x^{-1}$. Do not truncate prematurely or drop negative signs.
<!-- SLOW_UPDATE_END -->
