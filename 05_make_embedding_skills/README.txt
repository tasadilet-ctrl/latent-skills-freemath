Turning a text skill into an embedding skill
================================================================================
This folder is the method. Everything in 01_/02_/03_/04_ is just measurement;
this is the part that makes a claim.

RUN THEM IN ORDER
--------------------------------------------------------------------------------
  01_extract_from_placebo.sh          the CONTROLLED vector   (arm B1)
  02_extract_from_nothing.sh          the UNCONTROLLED vector (arm B2)
  03_extract_control_from_placebo.sh  the NULL vector         (the CONTROL)
        -> ../vectors/*.pt

  04_measure_fidelity.sh <vec>        which (layer, gamma) reproduces the skill
  05_check_degeneration.sh <vec>      ...and does not wreck generation
  06_check_skill_compliance.sh        optional: is the skill even being followed

Then take the chosen (layer, gamma) to the benchmark folders:
  ../01_livemath_direct/run_embed_from_placebo.sh <vec> <layers> <gamma>

WHAT A VECTOR IS
--------------------------------------------------------------------------------
Difference-in-means over a pool of neutral tasks, read at the final prompt
token, one direction per layer:

    v = E[h_l | with skill] - E[h_l | without]

At inference it is added back into the residual stream, scaled relative to the
activation norm:

    h <- h + gamma * ||h|| * v_hat

The pool is NEUTRAL tasks, not the benchmark's own questions. Extract on the
benchmark and the vector memorises the benchmark rather than carrying a skill.

THE THREE VECTORS ARE NOT INTERCHANGEABLE
--------------------------------------------------------------------------------
  from placebo  both sides carry length-matched filler text, so "a system
                prompt exists" cancels. What is left should be the procedure.
  from nothing  the contrast contains the procedure AND the presence of
                instructional text. Nothing separates them.
  CONTROL       built from the placebo itself. Contains no procedure at all.

The whole point is the comparison. On LiveMath, the uncontrolled arm carried
most of the text skill's apparent effect and the controlled arm did not --
which says the method transported the presence of instructions, not the
procedure. You cannot reach that conclusion, in either direction, without all
three.

WHY FIDELITY AND NOT ACCURACY CHOOSES THE SETTINGS
--------------------------------------------------------------------------------
    fidelity = 1 - KL(text || steered) / KL(text || plain)

Generate under the text skill, then ask how much closer steering gets the
model's token distribution to that than no steering does.

A skill worth two points on a 608-item 5-way benchmark cannot be separated
from noise by accuracy. Choosing layer and gamma by best accuracy is fitting
the test set. Fidelity measures whether the vector IS the skill, independent
of whether the skill helps.

Note what the LiveMath run found: fidelity did not predict effect. The 14B's
best vector scored +0.638 fidelity and -0.16 accuracy, while its text skill
gave +2.30. A faithful vector is not automatically a useful one. Report both.

THE TEACHER-FORCING HOLE, AND WHY 05_ EXISTS
--------------------------------------------------------------------------------
Fidelity is computed teacher-forced, one token at a time against a reference.
Free generation can have collapsed into repetition while fidelity still looks
healthy. 05_check_degeneration.sh sweeps the same grid and reports a
distinct-token ratio.

Choose the best fidelity AMONG SETTINGS THAT PASS 05_. Not the best overall.
