# Design notes for the skill files  (NOT model-visible)

These notes used to sit at the top of the .md skill files themselves, which meant
they were rendered into the system prompt and read by the model. That is a
contamination bug: it told the model about the experiment it was part of, and the
placebo went further and stated that it "carries no procedural content".
Everything in `skills/*.md` is model-visible text. Rationale lives here.

## decompose_verify.md
Written the way an automatic skill miner (EvoSkill / Trace2Skill style) would
produce it from successful GSM8K traces: the procedure is general, but the
wording and examples carry source-domain vocabulary. That baggage is what the
text arm drags into the out-of-domain evaluation, which is the effect under test.

## placebo_matched.md
A length- and register-matched control: same shape (headed sections, numbered
imperatives, similar token count) but no procedural content. Contrasting against
this rather than against no system message removes "a long system prompt is
present" from the extracted direction. Measured: at layer 0, ||v|| falls from
0.484 (vs nothing) to 0.142 (vs placebo) -- 71% of the shallow signal was
prompt-presence, not skill.

## compare_claims.md
The text skill for LiveMath (LiveMathematicianBench): 608 research-level maths
questions, each a 5-way choice over statements derived from a recent paper. The
distractor roles the source data encodes are weaker-but-true, plausible-but-false
and an off-topic trap, so the discriminating procedure is quantifier bookkeeping
and strength ordering, not arithmetic -- which is why `decompose_verify.md` is
the wrong skill here and a new one was written.

Kept to 7 numbered imperatives at ~260 words so it stays close to
`placebo_matched.md` (~228 words). The residual length gap is what the placebo
contrast cannot remove; it is smaller than the gap to no system message at all,
which is the comparison the two extraction arms make.

## compare_claims_v2.md
Revision after measuring v1 on the full 608. v1 scored 24.18% against a 25.99%
baseline (McNemar p=0.41 -- indistinguishable, not a real drop), but the error
profile showed it was not inert. Mapping every answer back to the distractor
role the source data labels (`weaker_true_label`, `wildcard_false_label`,
`template_used`):

                        baseline   v1
    correct               26.0%   24.2%
    wildcard (off-topic)  21.4%   21.5%
    weaker-but-true       18.3%   11.8%   <- v1's step 4 worked
    stronger-trap         14.3%   15.6%
    scope errors          12.8%   18.8%   <- and leaked to here

So v1 bought a real 6.5-point cut in the weaker-true trap and spent all of it
on over-claims and scope errors: it taught "prefer the stronger statement" with
no symmetric brake. v2 keeps the strength step but (a) puts a relevance screen
first, since a fifth of all answers go to an off-topic wildcard that v1 never
addressed, (b) makes scope auditing concrete rather than a clause inside
another step, and (c) states that over-claiming is false rather than strong.
The blanket "restate every candidate" step is gone: compliance with it was 100%
against a 10% baseline rate and it bought nothing.

NOTE on method: v2 was written after seeing v1's error profile on the same 608
items it is then scored on. That is test-set-informed, and the honest report
says so. Only the aggregate role histogram was used, never per-item labels, and
`report.py` also prints the late-month subset.

## compare_claims_v3.md
v2 scored 24.01% against v1's 24.18% and a 25.99% baseline -- no movement. The
role histogram shows why, and it is not that the skills are inert:

    role              base    v1     v2
    correct           26.0   24.2   24.0
    wildcard          21.4   21.5   17.4   <- v2's relevance screen worked
    weaker_true       18.3   11.8   20.7   <- and gave back v1's gain
    stronger_trap     14.3   15.6   14.5

Each version fixes one trap and reopens another while accuracy stays flat. The
mechanism is visible in v2's compliance: "reject over-claims" appears in 87% of
replies and competes with "prefer the strongest" for the same decision. Given
two preferences the model over-applies whichever is more salient, so v1
over-preferred strength and v2 under-preferred it.

v3 therefore replaces the competing pair with ONE criterion -- can the
candidate be derived from the hypotheses -- and makes strength ordering a
strictly downstream tiebreak among derivable candidates only. It keeps v2's
relevance screen, which is the one intervention that bought something without
costing something else.

If v3 also lands at ~24%, the honest reading is that on LiveMath this model has
a roughly fixed error budget that prompt-level procedure redistributes across
trap types without reducing. That is a reportable null, and it is measured
rather than asserted: three skills, three distinct compliance profiles, one
unchanged accuracy.

## compare_claims.md -- VERSION HISTORY AND A NAME COLLISION TO KNOW ABOUT

Consolidated to a single file on 2026-10-05. `compare_claims.md` now holds
what was previously `compare_claims_v3.md` -- "Derive First, Then Take the
Strongest That Survives". The two superseded drafts were deleted:

  v1  "Identify the Claim, Compare the Candidates, Eliminate"
      Scored ~24% on LiveMath against a 26.15% baseline -- i.e. it hurt.
      Its failure is informative: it ranked candidates by strength before
      checking derivability, so it reliably chose the strongest statement
      the hypotheses did not support.

  v2  "Screen for Relevance, Audit the Scope, Then Rank"
      Used as an ablation (the "text:v2" column in older matrices). Closer,
      but still mixed strength into the elimination step.

  v3  separates them: derive first (step 3), and let strength decide only
      among survivors (step 5). This is the final skill and the one every
      reported LiveMath text cell used.

** THE COLLISION. ** Before this consolidation the name `compare_claims.md`
meant v1 -- the draft that HURT. It now means v3. Result files written before
2026-10-05 that record `"skill": "compare_claims.md"` are v1 runs and must not
be merged with new ones. The kit ships an empty results/ so this cannot arise
here; it matters only if you copy old result files in. Results naming
`compare_claims_v3.md` are the same text as today's `compare_claims.md`, and
src/matrix.py maps both to the plain "text" column.
