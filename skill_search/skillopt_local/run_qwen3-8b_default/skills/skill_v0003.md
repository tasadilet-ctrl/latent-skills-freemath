# Live Mathematical MCQ Heuristics

## Option Comparison

- **Meta-Option Awareness**: Treat options phrased as 'One of the remaining options is correct, but a stronger result can be proven' as a primary candidate, especially when the question asks for the 'strongest statement', 'complete classification', 'exact characterization', or a universal property that 'holds for every such choice'. Do not dismiss them as 'invalid', 'non-mathematical', or 'fallback' choices. In theorem-grounded MCQs, this option is frequently the correct answer when the concrete alternatives are true but represent intermediate bounds, weaker theorems, or suboptimal statements. If multiple plausible concrete options appear, strongly consider this meta-option over them.
- Compare all options before committing. The correct choice is the strongest mathematically valid statement. Distractors often appear precise but are actually weaker due to added conditions, or they are meta-options correctly identifying that a stronger theorem exists.

- **Defining 'Strongest'**: 'Strongest' means the most precise claim that is actually provable. Do not confuse rhetorical or apparent strength with mathematical truth. Options that claim higher regularity, global bounds, or exact equalities when only weaker/local results are standard are likely distractors. The correct answer typically features strict inequalities, existential quantifiers, or carefully restricted domains that match the theorem's actual limits.
- Track exact quantifiers such as "there exists", "for every", "if and only if", and "exactly when".

## Theorem-Level Precision
- Check whether an option weakens the conclusion by dropping a characterization, equality clause, full equivalence, or by imposing unnecessary domain restrictions.
- Check whether an option overstates the theorem by upgrading regularity, removing scale restrictions, or changing an existential statement into a universal one.

- **Reject Unverified Extra Claims**: Do not select options that add explicit constants, norm bounds, extra hypotheses, or domain limits unless strictly provable from the given assumptions. Theorems are typically stated in their broadest valid form; adding conditions usually creates a weaker distractor.
- **Exact Equalities vs. Strict Inequalities**: Be cautious with exact equalities in exponents or bounds. In regularity and existence theorems, strict inequalities are often the correct strongest provable statement due to technical optimality gaps, whereas exact equalities may overstate the result.

## Hypotheses
- Verify the hypotheses and domain carefully. Distractors often keep the theorem shape but alter the required assumptions.
- Pay close attention to equality cases, extremal conditions, and whether a result applies to the full family or only a restricted subfamily.

## Final Answer
- Output the final answer as the single option label only.

- **Fidelity Over Logical Strength**: Do not rank options by logical or rhetorical strength. The correct choice is the one that precisely matches the established theorem, even if it appears logically weaker or less detailed. A logically stronger statement that adds unproven conditions, estimates, or converses is a distractor.
- **Triviality Filter**: Reject options that are trivially true by set-theoretic or logical definition (e.g., $A = A \cap B$) as they lack substantive mathematical content and are typically distractors.

<!-- SLOW_UPDATE_START -->
**Meta-Option Protocol**: Only apply to options explicitly phrased as "One of the remaining options is correct, but a stronger result can be proven." In "strongest statement" questions, this is almost always correct. Briefly verify that the concrete options are mathematically plausible but weaker or incomplete, then select it. Do not skip reasoning; use it to confirm the pattern and avoid misidentifying concrete options as meta-options.

**Override the "Strongest Concrete Option" Bias**: When the meta-option is absent, deliberately reject the logically strongest or most detailed concrete statement. It is a distractor. The correct answer precisely matches the established theorem, which often appears "weaker" due to necessary restrictions, strict inequalities, or conditional clauses.

**Theorem Boundary Verification Checklist**: Before selecting a concrete option, actively scan for overstatement traps:
- Does it claim global/universal validity where the theorem only guarantees local/existential results?
- Does it replace a strict inequality with a non-strict one, or add exact equalities where bounds are standard?
- Does it introduce unnecessary regime splits, finer classifications, or extra cases not supported by the literature?
- If any apply, discard it. Select the option that conserves the theorem's exact limits.

**Output Discipline**: Always output the final answer strictly as `<answer>X</answer>` on a single line. Never use `$$`, `\boxed{}`, or markdown formatting for the label. This prevents parsing failures.
<!-- SLOW_UPDATE_END -->
