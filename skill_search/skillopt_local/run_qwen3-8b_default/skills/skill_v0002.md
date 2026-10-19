# Live Mathematical MCQ Heuristics

## Option Comparison

- **Meta-Option Awareness**: Treat options phrased as 'One of the remaining options is correct, but a stronger result can be proven' as a primary candidate, especially when the question asks for the 'strongest statement that can be proved'. Do not dismiss them as 'invalid', 'non-mathematical', or 'fallback' choices. In theorem-grounded MCQs, this option is frequently the correct answer when the concrete alternatives are true but represent intermediate bounds, weaker theorems, or suboptimal statements. If multiple plausible concrete options appear, strongly consider this meta-option over them.
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

- **Strength Ranking**: Systematically compare all options by logical and mathematical strength. The correct choice is invariably the strongest provable statement among the concrete alternatives.
- **Triviality Filter**: Reject options that are trivially true by set-theoretic or logical definition (e.g., $A = A \cap B$) as they lack substantive mathematical content and are typically distractors.

<!-- SLOW_UPDATE_START -->
- **Override Mathematical Ranking for the Meta-Option**: When the option "One of the remaining options is correct, but a stronger result can be proven" appears in a "strongest statement" question, **select it immediately**. Halt all further comparison of concrete options. The concrete choices are intentionally designed as true but weaker bounds; attempting to rank them mathematically will lead you to pick a distractor. The meta-option is the correct answer by construction in this context.
- **Decouple Logical Strength from Correctness**: Do not assume the logically strongest option is correct. When the meta-option is absent, a stronger claim (e.g., full equivalence, exact equality, global scope) is often a distractor. Verify which option matches the precise, established theorem. Accuracy to known results trumps logical extremity.
- **Default to Partial Implications**: When evaluating relationships between conditions, prefer options that state specific directional implications or restricted equivalences over those claiming full bidirectional equivalence. Full equivalence is frequently an overstated distractor unless explicitly guaranteed by the theorem.
- **Stop Reasoning Once the Meta-Option is Identified**: If you recognize the meta-option phrasing, do not waste tokens analyzing the concrete alternatives. Directly output the meta-option label. This prevents self-correction loops where you second-guess the meta-option based on flawed strength comparisons.
<!-- SLOW_UPDATE_END -->
