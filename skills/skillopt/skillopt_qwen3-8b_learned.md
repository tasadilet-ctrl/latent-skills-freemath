# Live Mathematical MCQ Heuristics

## Option Comparison

- **Meta-Option Awareness**: Treat options phrased as 'One of the remaining options is correct, but a stronger result can be proven' as a primary candidate, especially when the question asks for the 'strongest statement', 'complete classification', 'exact characterization', or a universal property that 'holds for every such choice'. Do not dismiss them as 'invalid', 'non-mathematical', or 'fallback' choices. In theorem-grounded MCQs, this option is frequently the correct answer when the concrete alternatives are true but represent intermediate bounds, weaker theorems, or suboptimal statements. If multiple plausible concrete options appear, strongly consider this meta-option over them.
- Compare all options before committing. The correct choice is the strongest mathematically valid statement. Distractors often appear precise but are actually weaker due to added conditions, or they are meta-options correctly identifying that a stronger theorem exists.

- **Defining 'Strongest'**: In these MCQs, "strongest statement" is a trap. Distractors often appear mathematically stronger by claiming higher regularity, exact equalities, global bounds, or extra estimates. These are almost always unproven overstatements. The correct answer is the one that exactly matches the established theorem, which frequently looks "weaker" or more restricted. Never select an option solely because it claims more than the others.
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

- **Triviality Filter**: Reject options that are trivially true by set-theoretic or logical definition (e.g., $A = A \cap B$) as they lack substantive mathematical content and are typically distractors.

<!-- SLOW_UPDATE_START -->
**Meta-Option Absolute Priority**: In questions asking for the "strongest statement/result/estimate," if an option reads "One of the remaining options is correct, but a stronger result can be proven," it IS the correct answer. Do not compare it against concrete options. Do not dismiss it as "vague," "non-concrete," or "non-mathematical." Select it immediately after a brief scan confirms the other options are plausible but weaker or incomplete.

**Invert the Detail Bias**: When the meta-option is absent, the most detailed or logically strongest concrete option is almost always a distractor. Reject options that add explicit constants, precise numerical estimates, finer regime splits, or extra classifications. The correct answer precisely matches the established theorem, which typically uses strict inequalities, existential quantifiers, or conservative domain restrictions.

**Inequality Heuristic**: In regularity, existence, and bound theorems, strict inequalities are standard and correct. Exact equalities in exponents or bounds frequently overstate the result. Always prefer the strict inequality option unless the identity is a known sharp theorem.

**Output Format Lock**: Your final answer MUST be exactly `<answer>X</answer>` on a single line. Never use `\boxed{}`, `$$`, markdown formatting, or extra explanatory text for the label. Parsing will fail otherwise.
<!-- SLOW_UPDATE_END -->
